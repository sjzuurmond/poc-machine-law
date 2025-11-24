"""Page Object Model for Scenario UI interactions"""

from playwright.sync_api import Page, expect


class ScenarioPage:
    """Page Object for scenario-related UI interactions"""

    def __init__(self, page: Page):
        self.page = page
        self.base_url = "http://localhost:8000"

        # Scenario toggle
        self.scenario_toggle_checkbox = self.page.locator("input[x-model='scenarioMode']")
        self.scenario_toggle_label = self.page.locator("text=🧪 Scenario modus")

        # Modal
        self.modal_container = self.page.locator("#modal-container")

        # Scenario panel
        self.scenario_panel_selector = "div.bg-purple-50"
        self.scenario_panel = self.page.locator(self.scenario_panel_selector)

        # Scenario panel elements
        self.scenario_clear_button = self.page.locator("button >> text=Wissen")
        self.scenario_compare_button = self.page.locator("button >> text=Vergelijk")

    def navigate_to_homepage(self) -> None:
        """Navigate to the homepage"""
        self.page.goto(self.base_url, timeout=2000)
        self.page.wait_for_load_state("domcontentloaded", timeout=1000)

    def enable_scenario_mode(self) -> None:
        """Enable scenario mode via toggle"""
        if not self.scenario_toggle_checkbox.is_checked():
            self.scenario_toggle_checkbox.check()
            # Wait for page reload
            self.page.wait_for_load_state("domcontentloaded", timeout=2000)

    def disable_scenario_mode(self) -> None:
        """Disable scenario mode via toggle"""
        if self.scenario_toggle_checkbox.is_checked():
            self.scenario_toggle_checkbox.uncheck()
            # Wait for page reload
            self.page.wait_for_load_state("domcontentloaded", timeout=2000)

    def is_scenario_mode_enabled(self) -> bool:
        """Check if scenario mode is enabled"""
        return self.scenario_toggle_checkbox.is_checked()

    def click_test_button_for_field(self, field_label: str) -> None:
        """
        Click the test button for a specific field.

        Args:
            field_label: The label of the field to test (e.g., "Inkomen Box 1")
        """
        # Find the test button near the field label
        test_button = self.page.locator(
            f"div:has-text('{field_label}') >> button:has-text('🧪 Test')"
        ).first

        test_button.click()

        # Wait for modal to appear
        self.page.wait_for_selector("#modal-container > div", timeout=2000)

    def fill_scenario_form(self, new_value: str) -> None:
        """
        Fill the scenario form with a new value.

        Args:
            new_value: The new value to enter
        """
        # Wait for form to be visible
        form_input = self.modal_container.locator("input[name='value'], textarea[name='value']").first
        form_input.wait_for(timeout=2000)

        # Clear and fill
        form_input.clear()
        form_input.fill(new_value)

    def submit_scenario_form(self) -> None:
        """Submit the scenario form"""
        submit_button = self.modal_container.locator("button[type='submit']").first
        submit_button.click()

        # Wait for success message or reload
        self.page.wait_for_timeout(1000)

    def close_scenario_modal(self) -> None:
        """Close the scenario modal"""
        close_button = self.modal_container.locator("button:has-text('Annuleren')").first
        close_button.click()
        self.page.wait_for_timeout(500)

    def is_scenario_panel_visible(self) -> bool:
        """Check if the scenario panel is visible"""
        return self.scenario_panel.is_visible()

    def get_scenario_panel_value_count(self) -> int:
        """Get the number of scenario values shown in the panel"""
        value_items = self.scenario_panel.locator("li").all()
        return len(value_items)

    def clear_scenario(self) -> None:
        """Click the clear scenario button"""
        self.scenario_clear_button.click()
        self.page.wait_for_timeout(1000)

    def open_scenario_comparison(self) -> None:
        """Open the scenario comparison view"""
        self.scenario_compare_button.click()
        self.page.wait_for_timeout(1000)

    def expect_scenario_panel_visible(self) -> None:
        """Expect the scenario panel to be visible"""
        expect(self.scenario_panel).to_be_visible()

    def expect_scenario_panel_not_visible(self) -> None:
        """Expect the scenario panel to not be visible"""
        expect(self.scenario_panel).not_to_be_visible()

    def expect_test_buttons_visible(self) -> None:
        """Expect test buttons to be visible"""
        test_button = self.page.locator("button:has-text('🧪 Test')").first
        expect(test_button).to_be_visible()

    def expect_test_buttons_not_visible(self) -> None:
        """Expect test buttons to not be visible"""
        test_button = self.page.locator("button:has-text('🧪 Test')").first
        expect(test_button).not_to_be_visible()

    def get_field_value(self, field_label: str) -> str:
        """
        Get the current value of a field.

        Args:
            field_label: The label of the field

        Returns:
            The current value as string
        """
        field_div = self.page.locator(f"div:has-text('{field_label}')").first
        return field_div.text_content()

    def expect_field_has_value(self, field_label: str, expected_value: str) -> None:
        """
        Expect a field to have a specific value.

        Args:
            field_label: The label of the field
            expected_value: The expected value
        """
        field_div = self.page.locator(f"div:has-text('{field_label}')").first
        expect(field_div).to_contain_text(expected_value)

    def expect_modal_visible(self) -> None:
        """Expect the modal to be visible"""
        expect(self.modal_container.locator("div").first).to_be_visible()

    def expect_modal_not_visible(self) -> None:
        """Expect the modal to not be visible"""
        modal_content = self.modal_container.locator("div").first
        expect(modal_content).not_to_be_visible()

    def select_boolean_value(self, value: bool) -> None:
        """
        Select a boolean value in the scenario form.

        Args:
            value: True or False
        """
        radio_value = "true" if value else "false"
        radio_input = self.modal_container.locator(f"input[type='radio'][value='{radio_value}']")
        radio_input.check()

    def fill_number_value(self, value: int | float) -> None:
        """
        Fill a number value in the scenario form.

        Args:
            value: The number to enter
        """
        number_input = self.modal_container.locator("input[type='number']")
        number_input.fill(str(value))

    def fill_date_value(self, date: str) -> None:
        """
        Fill a date value in the scenario form.

        Args:
            date: The date in YYYY-MM-DD format
        """
        date_input = self.modal_container.locator("input[type='date']")
        date_input.fill(date)

    def get_law_tile(self, law_name: str) -> any:
        """
        Get a specific law tile by name.

        Args:
            law_name: The name of the law

        Returns:
            Locator for the law tile
        """
        return self.page.locator(f"div.law-result-card:has-text('{law_name}')").first

    def expect_law_tile_visible(self, law_name: str) -> None:
        """
        Expect a law tile to be visible.

        Args:
            law_name: The name of the law
        """
        tile = self.get_law_tile(law_name)
        expect(tile).to_be_visible()

    def wait_for_page_reload(self) -> None:
        """Wait for page to reload after scenario changes"""
        self.page.wait_for_load_state("domcontentloaded", timeout=3000)
        self.page.wait_for_timeout(500)

    def get_comparison_table(self) -> any:
        """Get the comparison table"""
        return self.page.locator("table")

    def expect_comparison_visible(self) -> None:
        """Expect the comparison table to be visible"""
        expect(self.get_comparison_table()).to_be_visible()
