<?php if (!defined('ABSPATH')) { exit; } ?>
<!doctype html><html <?php language_attributes(); ?>><head>
<meta charset="<?php bloginfo('charset'); ?>"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow"><title><?php esc_html_e('Log out', 'kklidi-members'); ?></title><?php wp_head(); ?>
</head><body <?php body_class('kklidi-members-page kklidi-members-page--logout'); ?>><?php wp_body_open(); ?>
<main class="kklidi-members-main"><section class="kklidi-members-card" aria-labelledby="kklidi-members-page-title"><header class="kklidi-members-header"><h1 id="kklidi-members-page-title"><?php esc_html_e('Log out', 'kklidi-members'); ?></h1></header>
<?php if ($message !== '') : ?><p class="kklidi-members-notice kklidi-members-notice--error" role="alert"><?php echo esc_html($message); ?></p><?php endif; ?>
<form class="kklidi-members-form" method="post"><input type="hidden" name="kklidi_members_logout" value="1"><input type="hidden" name="redirect_to" value="<?php echo esc_attr($redirect); ?>"><?php wp_nonce_field('kklidi_members_logout', '_kklidi_members_logout_nonce'); ?><button class="kklidi-members-button" type="submit"><?php esc_html_e('Log out', 'kklidi-members'); ?></button></form>
</section></main><?php wp_footer(); ?></body></html>
