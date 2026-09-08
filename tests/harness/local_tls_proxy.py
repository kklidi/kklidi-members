"""Small test-only TLS reverse proxy for the fixed MAMP sandbox."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ssl


HOP_BY_HOP = {
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade',
}


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    backend_host = '127.0.0.1'
    backend_port = 8888
    public_origin = 'https://localhost:9443'
    backend_origin = 'http://localhost:8888'
    harness_token = ''

    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def log_message(self, format_string, *args):
        return

    def _proxy(self):
        length = int(self.headers.get('Content-Length', '0') or '0')
        body = self.rfile.read(length) if length else None
        headers = {name: value for name, value in self.headers.items()
                   if name.lower() not in HOP_BY_HOP
                   and name.lower() not in {'host', 'x-forwarded-for', 'x-forwarded-proto',
                                            'x-kklidi-harness-tls'}}
        headers.update({
            'Host': 'localhost:8888',
            'X-Forwarded-For': '127.0.0.1',
            'X-Forwarded-Proto': 'https',
            'X-KKLIDI-Harness-TLS': self.harness_token,
        })
        connection = http.client.HTTPConnection(self.backend_host, self.backend_port, timeout=30)
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read()
            self.send_response(response.status, response.reason)
            for name, value in response.getheaders():
                lowered = name.lower()
                if lowered in HOP_BY_HOP or lowered in {'content-length', 'strict-transport-security'}:
                    continue
                if lowered == 'location':
                    value = value.replace(self.backend_origin, self.public_origin)
                self.send_header(name, value)
            self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(payload)
        finally:
            connection.close()


def create_server(certificate, private_key, token):
    handler = type('BoundProxyHandler', (ProxyHandler,), {'harness_token': token})
    server = ThreadingHTTPServer(('127.0.0.1', 9443), handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(certificate), keyfile=str(private_key))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server
