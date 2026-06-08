###########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

import os
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from regression.feature_utils.base_feature_test import BaseFeatureTest
from regression.python_test_utils import test_utils
from regression.python_test_utils import test_gui_helper
from regression.feature_utils.locators import NavMenuLocators, PreferencesLocators


class BackupRestoreTest(BaseFeatureTest):
    """This class tests Backup and Restore functionality for PostgreSQL and EPAS"""

    scenarios = [
        ("Test Backup and Restore for PostgreSQL", dict(
            database_name="backup_restore_pg_db",
            server_type='pg',
            is_xss_check=False,
        )),
        ("Test Backup and Restore for EPAS", dict(
            database_name="backup_restore_epas_db",
            server_type='epas',
            is_xss_check=False,
        )),
        ("Test XSS in Backup and Restore for PostgreSQL", dict(
            database_name="<h1>backup_restore_xss</h1>",
            server_type='pg',
            is_xss_check=True,
        )),
        ("Test XSS in Backup and Restore for EPAS", dict(
            database_name="<h1>backup_restore_xss</h1>",
            server_type='epas',
            is_xss_check=True,
        )),
    ]

    def before(self):
        if self.server['default_binary_paths'] is None:
            self.skipTest(
                "default_binary_paths is not set for the server {0}".format(
                    self.server['name']
                )
            )

        if '<' in self.database_name and os.name == 'nt':
            self.skipTest(
                "HTML tags '<' and '>' in object name does not "
                "work for windows so skipping the test case"
            )

        connection = test_utils.get_db_connection(
            self.server['db'],
            self.server['username'],
            self.server['db_password'],
            self.server['host'],
            self.server['port'],
            self.server['sslmode']
        )
        test_utils.drop_database(connection, self.database_name)
        db_id = test_utils.create_database(self.server, self.database_name)
        if not db_id:
            self.assertEqual(0, 1, "Database {} is not created".format(self.database_name))
        self.page.add_server(self.server)
        self.wait = WebDriverWait(self.page.driver, 20)

    def runTest(self):
        self.page.expand_database_node("Server", self.server['name'],
                                       self.server['db_password'],
                                       self.database_name)

        # Backup
        self.initiate_backup()
        test_gui_helper.wait_for_process_start(self)
        test_gui_helper.open_process_details(self)

        backup_file = None
        # Check for XSS in Backup details
        if self.is_xss_check:
            self._check_detailed_window_for_xss('Backup')
        else:
            message = self.page.find_by_css_selector(
                NavMenuLocators.process_watcher_detailed_message_css).text
            command = self.page.find_by_css_selector(
                NavMenuLocators.process_watcher_detailed_command_css).text

            self.assertIn(self.server['name'], str(message))
            self.assertIn("from database '{}'".format(self.database_name), str(message))
            if os.name != 'nt':
                self.assertIn("test_backup", str(command))
            self.assertIn("pg_dump", str(command))
            if command:
                backup_file = command[int(command.find('--file')) + 8:int(command.find('--host')) - 2]

        test_gui_helper.close_process_watcher(self)

        # Restore
        self.initiate_restore()
        test_gui_helper.wait_for_process_start(self)
        test_gui_helper.open_process_details(self)

        # Check for XSS in Restore details
        if self.is_xss_check:
            self._check_detailed_window_for_xss('Restore')
        else:
            message = self.page.find_by_css_selector(
                NavMenuLocators.process_watcher_detailed_message_css).text
            command = self.page.find_by_css_selector(
                NavMenuLocators.process_watcher_detailed_command_css).text

            self.assertIn(self.server['name'], str(message))
            if os.name != 'nt':
                self.assertIn("test_backup", str(command))
            self.assertIn("pg_restore", str(command))

        test_gui_helper.close_process_watcher(self)

        if backup_file is not None and os.path.isfile(backup_file):
            os.remove(backup_file)

    def after(self):
        try:
            self.page.remove_server(self.server)
        except Exception:
            print("BackupRestoreTest - Exception occurred in after method")
        finally:
            connection = test_utils.get_db_connection(
                self.server['db'],
                self.server['username'],
                self.server['db_password'],
                self.server['host'],
                self.server['port'],
                self.server['sslmode']
            )
            test_utils.drop_database(connection, self.database_name)

    def _check_detailed_window_for_xss(self, tool_name):
        source_code = self.page.find_by_css_selector(
            NavMenuLocators.process_watcher_detailed_command_css
        ).get_attribute('innerHTML')
        self._check_escaped_characters(
            source_code,
            '&lt;h1&gt;backup_restore_xss&lt;/h1&gt;',
            '{0} detailed window'.format(tool_name)
        )

    def initiate_backup(self):
        self.page.retry_click(
            (By.CSS_SELECTOR, NavMenuLocators.tools_menu_css),
            (By.CSS_SELECTOR, NavMenuLocators.backup_obj_css))
        backup_object = self.wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, NavMenuLocators.backup_obj_css)))
        backup_object.click()

        self.assertFalse(self.page.check_utility_error(),
                         'Binary path is not configured.')

        # Enter the file name of the backup to be taken
        self.wait.until(EC.visibility_of_element_located(
            (By.NAME, NavMenuLocators.backup_filename_txt_box_name)))
        element = self.wait.until(EC.element_to_be_clickable(
            (By.NAME, NavMenuLocators.backup_filename_txt_box_name)))
        element.click()
        self.page.fill_input_by_field_name(
            NavMenuLocators.backup_filename_txt_box_name,
            "test_backup", input_keys=True, loose_focus=True)

        # Click on the take Backup button
        take_backup = self.page.find_by_css_selector(
            NavMenuLocators.backup_btn)
        click = True
        retry = 3
        while click and retry > 0:
            try:
                take_backup.click()
                if self.page.wait_for_element_to_disappear(
                    lambda driver: driver.find_element(
                        By.CSS_SELECTOR,
                        ".dock-fbox div[title^='Backup']")):
                    click = False
            except Exception:
                retry -= 1

    def initiate_restore(self):
        tools_menu = self.driver.find_element(
            By.CSS_SELECTOR, NavMenuLocators.tools_menu_css)
        tools_menu.click()

        restore_obj = self.page.find_by_css_selector(
            NavMenuLocators.restore_obj_css)
        restore_obj.click()

        self.assertFalse(self.page.check_utility_error(),
                         'Binary path is not configured.')

        self.wait.until(EC.visibility_of_element_located(
            (By.NAME, NavMenuLocators.restore_file_name_txt_box_name)))
        self.wait.until(EC.element_to_be_clickable(
            (By.NAME, NavMenuLocators.restore_file_name_txt_box_name))).click()
        self.page.fill_input_by_field_name(
            NavMenuLocators.restore_file_name_txt_box_name,
            "test_backup", input_keys=True, loose_focus=True)

        # Click on the Restore button
        restore_btn = self.page.find_by_xpath(
            NavMenuLocators.restore_button_xpath)
        click = True
        retry = 3
        while click and retry > 0:
            try:
                restore_btn.click()
                if self.page.wait_for_element_to_disappear(
                    lambda driver: driver.find_element(
                        By.NAME,
                        NavMenuLocators.restore_file_name_txt_box_name)):
                    click = False
            except Exception:
                retry -= 1

    def _check_escaped_characters(self, source_code, string_to_find, source):
        # For XSS we need to search against element's html code
        assert source_code.find(string_to_find) != -1, "{0} might be vulnerable to XSS ".format(source)
