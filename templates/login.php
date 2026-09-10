<?php

if (!defined('ABSPATH')) {
	exit;
}
?>
<!doctype html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo('charset'); ?>">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<meta name="robots" content="noindex, nofollow">
	<title><?php echo esc_html(sprintf(__('%s Login', 'kklidi-members'), get_bloginfo('name'))); ?></title>
	<?php wp_head(); ?>
</head>
<body <?php body_class('kklidi-members-page kklidi-members-page--login'); ?>>
<?php wp_body_open(); ?>
	<main class="kklidi-members-main">
		<section class="kklidi-members-card" aria-labelledby="kklidi-members-page-title">
			<header class="kklidi-members-header"><p class="kklidi-members-eyebrow"><a class="kklidi-members-brand" href="<?php echo esc_url($home_url); ?>"><?php echo esc_html(get_bloginfo('name')); ?></a></p><h1 id="kklidi-members-page-title"><?php esc_html_e('Log in', 'kklidi-members'); ?></h1><p><?php esc_html_e('Enter your account details to continue.', 'kklidi-members'); ?></p></header>
			<?php if ($notice !== '') : ?><p class="kklidi-members-notice" role="status"><?php echo esc_html($notice); ?></p><?php endif; ?>
			<?php if ($message !== '') : ?><p class="kklidi-members-notice kklidi-members-notice--error" role="alert"><?php echo esc_html($message); ?></p><?php endif; ?>
			<?php if ($message_html !== '') : ?><div class="kklidi-members-notice kklidi-members-notice--error" role="alert"><?php echo wp_kses_post($message_html); ?></div><?php endif; ?>
			<?php if ($field_errors !== array()) : ?><div class="kklidi-members-field-errors" role="alert"><p><?php esc_html_e('Please correct the highlighted fields.', 'kklidi-members'); ?></p><ul><?php foreach ($field_errors as $field => $field_error) : ?><li><a href="#kklidi-members-<?php echo esc_attr($field); ?>"><?php echo esc_html($field_error); ?></a></li><?php endforeach; ?></ul></div><?php endif; ?>
			<form class="kklidi-members-form" method="post" action="<?php echo esc_url($action_url); ?>" data-kklidi-members-login>
				<?php wp_nonce_field('kklidi_members_login', '_kklidi_members_login_nonce'); ?>
				<?php echo $guest_fields; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- generated escaped fields. ?>
				<input type="hidden" name="kklidi_members_login" value="1"><input type="hidden" name="redirect_to" value="<?php echo esc_attr($redirect_to); ?>">
				<label class="kklidi-members-field" for="kklidi-members-identifier"><?php esc_html_e('Username or email', 'kklidi-members'); ?><input id="kklidi-members-identifier" name="kklidi_members_identifier" type="text" autocomplete="username" value="<?php echo esc_attr($identifier); ?>" required<?php echo isset($field_errors['identifier']) ? ' aria-invalid="true" aria-describedby="kklidi-members-identifier-error"' : ''; ?>><?php if (isset($field_errors['identifier'])) : ?><span class="kklidi-members-field-error" id="kklidi-members-identifier-error"><?php echo esc_html($field_errors['identifier']); ?></span><?php endif; ?></label>
				<div class="kklidi-members-field"><label for="kklidi-members-password"><?php esc_html_e('Password', 'kklidi-members'); ?></label><div class="kklidi-members-password-control"><input id="kklidi-members-password" name="kklidi_members_password" type="password" autocomplete="current-password" required<?php echo isset($field_errors['password']) ? ' aria-invalid="true" aria-describedby="kklidi-members-password-error"' : ''; ?> data-kklidi-members-password><button class="kklidi-members-password-toggle" type="button" data-kklidi-members-password-toggle aria-controls="kklidi-members-password" aria-pressed="false" aria-label="<?php esc_attr_e('Show password', 'kklidi-members'); ?>" data-show-label="<?php esc_attr_e('Show password', 'kklidi-members'); ?>" data-hide-label="<?php esc_attr_e('Hide password', 'kklidi-members'); ?>"><svg class="kklidi-members-icon--on" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2.2 12s3.5-6 9.8-6 9.8 6 9.8 6-3.5 6-9.8 6-9.8-6-9.8-6Zm9.8 3.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg><svg class="kklidi-members-icon--off" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m3 3 18 18M10.6 6.2A10.8 10.8 0 0 1 12 6c6.3 0 9.8 6 9.8 6a17 17 0 0 1-3.1 3.7M6.3 6.8C3.7 8.6 2.2 12 2.2 12s3.5 6 9.8 6a9.7 9.7 0 0 0 3-.5M9.9 9.9a3 3 0 0 0 4.2 4.2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button></div><?php if (isset($field_errors['password'])) : ?><span class="kklidi-members-field-error" id="kklidi-members-password-error"><?php echo esc_html($field_errors['password']); ?></span><?php endif; ?></div>
				<label class="kklidi-members-check"><input name="kklidi_members_remember" type="checkbox" value="1" <?php checked($remember); ?>> <?php esc_html_e('Remember me', 'kklidi-members'); ?></label>
				<button class="kklidi-members-button" type="submit"><?php esc_html_e('Log in', 'kklidi-members'); ?></button>
			</form>
			<nav class="kklidi-members-form-links kklidi-members-form-links--primary" aria-label="<?php esc_attr_e('Login help', 'kklidi-members'); ?>"><a href="<?php echo esc_url($password_reset_url); ?>"><?php esc_html_e('Forgot your password?', 'kklidi-members'); ?></a></nav><nav class="kklidi-members-form-links kklidi-members-form-links--secondary" aria-label="<?php esc_attr_e('Account links', 'kklidi-members'); ?>"><a href="<?php echo esc_url($register_url); ?>"><?php esc_html_e('Create an account', 'kklidi-members'); ?></a></nav><nav class="kklidi-members-form-links kklidi-members-form-links--tertiary" aria-label="<?php esc_attr_e('Site navigation', 'kklidi-members'); ?>"><a class="kklidi-members-link--tertiary" href="<?php echo esc_url($home_url); ?>"><?php esc_html_e('Back to site', 'kklidi-members'); ?></a></nav>
		</section>
	</main>
	<?php wp_footer(); ?>
</body>
</html>
