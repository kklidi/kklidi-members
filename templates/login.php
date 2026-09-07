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
			<header class="kklidi-members-header"><h1 id="kklidi-members-page-title"><?php esc_html_e('Log in', 'kklidi-members'); ?></h1></header>
			<?php if ($message !== '') : ?><p class="kklidi-members-notice kklidi-members-notice--error" role="alert"><?php echo esc_html($message); ?></p><?php endif; ?>
			<?php if ($message_html !== '') : ?><div class="kklidi-members-notice kklidi-members-notice--error" role="alert"><?php echo wp_kses_post($message_html); ?></div><?php endif; ?>
			<form class="kklidi-members-form" method="post" action="<?php echo esc_url($action_url); ?>" data-kklidi-members-login>
				<?php wp_nonce_field('kklidi_members_login', '_kklidi_members_login_nonce'); ?>
				<?php echo $guest_fields; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- generated escaped fields. ?>
				<input type="hidden" name="kklidi_members_login" value="1"><input type="hidden" name="redirect_to" value="<?php echo esc_attr($redirect_to); ?>">
				<label class="kklidi-members-field" for="kklidi-members-identifier"><?php esc_html_e('Username or email', 'kklidi-members'); ?><input id="kklidi-members-identifier" name="kklidi_members_identifier" type="text" autocomplete="username" value="<?php echo esc_attr($identifier); ?>" required></label>
				<label class="kklidi-members-field" for="kklidi-members-password"><?php esc_html_e('Password', 'kklidi-members'); ?><input id="kklidi-members-password" name="kklidi_members_password" type="password" autocomplete="current-password" required></label>
				<label class="kklidi-members-check"><input name="kklidi_members_remember" type="checkbox" value="1"> <?php esc_html_e('Remember me', 'kklidi-members'); ?></label>
				<button class="kklidi-members-button" type="submit"><?php esc_html_e('Log in', 'kklidi-members'); ?></button>
			</form>
		</section>
	</main>
	<?php wp_footer(); ?>
</body>
</html>
