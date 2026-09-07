<?php if (!defined('ABSPATH')) { exit; } ?>
<!doctype html>
<html <?php language_attributes(); ?>><head>
	<meta charset="<?php bloginfo('charset'); ?>"><meta name="viewport" content="width=device-width, initial-scale=1">
	<meta name="robots" content="noindex,nofollow"><title><?php esc_html_e('Register', 'kklidi-members'); ?></title><?php wp_head(); ?>
</head><body <?php body_class('kklidi-members-page kklidi-members-page--register'); ?>><?php wp_body_open(); ?>
<main class="kklidi-members-main"><section class="kklidi-members-card" aria-labelledby="kklidi-members-page-title">
	<header class="kklidi-members-header"><h1 id="kklidi-members-page-title"><?php esc_html_e('Register', 'kklidi-members'); ?></h1></header>
	<?php if ($message !== '') : ?><p class="kklidi-members-notice kklidi-members-notice--error" role="alert"><?php echo esc_html($message); ?></p><?php endif; ?>
	<?php if ($enabled) : ?><form class="kklidi-members-form" method="post"><input type="hidden" name="kklidi_members_register" value="1"><input type="hidden" name="request_id" value="<?php echo esc_attr($request_id); ?>">
		<?php wp_nonce_field('kklidi_members_register', '_kklidi_members_register_nonce'); ?><?php echo $guest_fields; // phpcs:ignore ?>
		<label class="kklidi-members-field"><?php esc_html_e('Email', 'kklidi-members'); ?><input type="email" name="email" autocomplete="email" required></label>
		<label class="kklidi-members-field"><?php esc_html_e('Password', 'kklidi-members'); ?><input type="password" name="password" autocomplete="new-password" minlength="12" required></label>
		<label class="kklidi-members-field"><?php esc_html_e('Confirm password', 'kklidi-members'); ?><input type="password" name="password_confirm" autocomplete="new-password" minlength="12" required></label>
		<label class="kklidi-members-field"><?php esc_html_e('First name', 'kklidi-members'); ?><input name="first_name" autocomplete="given-name" required></label>
		<label class="kklidi-members-field"><?php esc_html_e('Last name', 'kklidi-members'); ?><input name="last_name" autocomplete="family-name"></label>
		<label class="kklidi-members-field"><?php esc_html_e('Display name', 'kklidi-members'); ?><input name="display_name" autocomplete="nickname" required></label>
		<label class="kklidi-members-field"><?php esc_html_e('Phone', 'kklidi-members'); ?><input name="phone" autocomplete="tel" inputmode="tel"></label>
		<section class="kklidi-members-section"><h2><?php esc_html_e('Required consent', 'kklidi-members'); ?></h2><div class="kklidi-members-document"><?php echo wp_kses_post($service_document['content']); ?></div><label class="kklidi-members-check"><input type="checkbox" name="consent_service" value="1" required> <?php esc_html_e('I agree to the service terms.', 'kklidi-members'); ?></label><div class="kklidi-members-document"><?php echo wp_kses_post($privacy_document['content']); ?></div><label class="kklidi-members-check"><input type="checkbox" name="consent_privacy" value="1" required> <?php esc_html_e('I agree to the privacy policy.', 'kklidi-members'); ?></label></section>
		<?php if ($marketing_document !== array()) : ?><section class="kklidi-members-section"><h2><?php esc_html_e('Optional consent', 'kklidi-members'); ?></h2><div class="kklidi-members-document"><?php echo wp_kses_post($marketing_document['content']); ?></div><label class="kklidi-members-check"><input type="checkbox" name="consent_marketing" value="1"> <?php esc_html_e('I agree to receive marketing information.', 'kklidi-members'); ?></label></section><?php endif; ?>
		<button class="kklidi-members-button" type="submit"><?php esc_html_e('Create account', 'kklidi-members'); ?></button>
	</form><?php endif; ?>
</section></main><?php wp_footer(); ?></body></html>
