<?php if (!defined('ABSPATH')) { exit; } ?>
<!doctype html><html <?php language_attributes(); ?>><head>
<meta charset="<?php bloginfo('charset'); ?>"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow"><title><?php esc_html_e('Change password', 'kklidi-members'); ?></title><?php wp_head(); ?>
</head><body <?php body_class('kklidi-members-page kklidi-members-page--password'); ?>><?php wp_body_open(); ?>
<main class="kklidi-members-main"><section class="kklidi-members-card" aria-labelledby="kklidi-members-page-title"><header class="kklidi-members-header"><h1 id="kklidi-members-page-title"><?php esc_html_e('Change password', 'kklidi-members'); ?></h1></header>
<?php if ($message !== '') : ?><p class="kklidi-members-notice kklidi-members-notice--error" role="alert"><?php echo esc_html($message); ?></p><?php endif; ?>
<form class="kklidi-members-form" method="post"><input type="hidden" name="kklidi_members_password" value="1"><?php wp_nonce_field('kklidi_members_password', '_kklidi_members_password_nonce'); ?>
<label class="kklidi-members-field"><?php esc_html_e('Current password', 'kklidi-members'); ?><input type="password" name="current_password" autocomplete="current-password" required></label>
<label class="kklidi-members-field"><?php esc_html_e('New password', 'kklidi-members'); ?><input type="password" name="new_password" autocomplete="new-password" minlength="12" required></label>
<label class="kklidi-members-field"><?php esc_html_e('Confirm new password', 'kklidi-members'); ?><input type="password" name="new_password_confirm" autocomplete="new-password" minlength="12" required></label>
<button class="kklidi-members-button" type="submit"><?php esc_html_e('Change password', 'kklidi-members'); ?></button></form>
<p class="kklidi-members-hint"><a href="<?php echo esc_url(kklidi_members_password_reset_url()); ?>"><?php esc_html_e('Forgot your password?', 'kklidi-members'); ?></a></p>
</section></main><?php wp_footer(); ?></body></html>
