-- Portable access follows the native SEC_PLAYER command; retain all other permissions.
UPDATE `command` SET `security` = 0 WHERE `name` = 'transmog portable' AND `security` = 1;
