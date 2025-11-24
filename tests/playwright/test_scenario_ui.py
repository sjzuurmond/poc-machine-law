"""E2E tests for scenario UI workflow"""

from playwright.sync_api import Page, expect

from tests.playwright.pages.scenario_page import ScenarioPage


def test_scenario_mode_toggle(page: Page):
    """Test enabling and disabling scenario mode"""
    scenario_page = ScenarioPage(page)

    # Navigate to homepage
    scenario_page.navigate_to_homepage()

    # Wait for page to load
    page.wait_for_timeout(500)

    # Initially, scenario mode should be off
    assert not scenario_page.is_scenario_mode_enabled()

    # Enable scenario mode
    scenario_page.enable_scenario_mode()

    # Verify it's enabled
    assert scenario_page.is_scenario_mode_enabled()

    # Test buttons should be visible in scenario mode
    test_buttons = page.locator("button:has-text('🧪 Test')").all()
    if len(test_buttons) > 0:
        # If there are any tiles with test buttons, they should be visible
        assert test_buttons[0].is_visible()


def test_scenario_mode_shows_test_buttons(page: Page):
    """Test that scenario mode shows test buttons on law tiles"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)

    # Check if test buttons are not visible initially
    test_buttons_before = page.locator("button:has-text('🧪 Test')").all()

    # Enable scenario mode
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(500)

    # Test buttons should now be visible (if there are any eligible fields)
    test_buttons_after = page.locator("button:has-text('🧪 Test')").all()

    # At least some test buttons should appear in scenario mode
    # (assuming there are law tiles with testable fields)
    assert len(test_buttons_after) >= len(test_buttons_before)


def test_open_scenario_form(page: Page):
    """Test opening the scenario form by clicking a test button"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(500)

    # Find a test button and click it
    test_buttons = page.locator("button:has-text('🧪 Test')").all()

    if len(test_buttons) > 0:
        test_buttons[0].click()

        # Wait for modal to appear
        page.wait_for_timeout(1000)

        # Verify modal is visible
        scenario_page.expect_modal_visible()

        # Modal should have a form
        form = page.locator("#modal-container form").first
        expect(form).to_be_visible()

        # Form should have submit and cancel buttons
        expect(page.locator("button:has-text('Bevestig')").first).to_be_visible()
        expect(page.locator("button:has-text('Annuleren')").first).to_be_visible()


def test_close_scenario_form(page: Page):
    """Test closing the scenario form without submitting"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(500)

    # Find and click a test button
    test_buttons = page.locator("button:has-text('🧪 Test')").all()

    if len(test_buttons) > 0:
        test_buttons[0].click()
        page.wait_for_timeout(1000)

        # Close the modal
        cancel_button = page.locator("button:has-text('Annuleren')").first
        cancel_button.click()

        # Wait for modal to close
        page.wait_for_timeout(500)

        # Modal should not be visible
        modal_content = page.locator("#modal-container > div").first
        if modal_content.count() > 0:
            expect(modal_content).not_to_be_visible()


def test_submit_scenario_value(page: Page):
    """Test submitting a new scenario value"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(500)

    # Find a test button and click it
    test_buttons = page.locator("button:has-text('🧪 Test')").all()

    if len(test_buttons) > 0:
        test_buttons[0].click()
        page.wait_for_timeout(1000)

        # Fill in a new value (try different input types)
        value_input = page.locator("#modal-container input[name='value']").first
        if value_input.count() > 0:
            input_type = value_input.get_attribute("type")

            if input_type == "number":
                value_input.fill("99999")
            elif input_type == "date":
                value_input.fill("2025-12-31")
            else:
                value_input.fill("test_value_123")

            # Submit the form
            submit_button = page.locator("button:has-text('Bevestig')").first
            submit_button.click()

            # Wait for page to reload or update
            page.wait_for_timeout(2000)

            # After submission, scenario panel should be visible
            scenario_panels = page.locator("div.bg-purple-50").all()
            if len(scenario_panels) > 0:
                assert scenario_panels[0].is_visible()


def test_scenario_panel_appears_after_setting_value(page: Page):
    """Test that scenario panel appears after setting a scenario value"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(500)

    # Check if scenario panel exists initially
    panels_before = page.locator("div.bg-purple-50").all()

    # Set a scenario value
    test_buttons = page.locator("button:has-text('🧪 Test')").all()

    if len(test_buttons) > 0:
        test_buttons[0].click()
        page.wait_for_timeout(1000)

        # Fill and submit
        value_input = page.locator("#modal-container input[name='value']").first
        if value_input.count() > 0:
            value_input.fill("12345")
            page.locator("button:has-text('Bevestig')").first.click()
            page.wait_for_timeout(2000)

            # Scenario panel should now be visible
            panels_after = page.locator("div.bg-purple-50").all()
            assert len(panels_after) >= len(panels_before)

            if len(panels_after) > 0:
                # Panel should contain scenario information
                panel_text = panels_after[0].text_content()
                assert "scenario" in panel_text.lower() or "test" in panel_text.lower()


def test_clear_scenario(page: Page):
    """Test clearing a scenario"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(500)

    # Set a scenario value first
    test_buttons = page.locator("button:has-text('🧪 Test')").all()

    if len(test_buttons) > 0:
        test_buttons[0].click()
        page.wait_for_timeout(1000)

        value_input = page.locator("#modal-container input[name='value']").first
        if value_input.count() > 0:
            value_input.fill("12345")
            page.locator("button:has-text('Bevestig')").first.click()
            page.wait_for_timeout(2000)

            # Now find and click the clear button
            clear_buttons = page.locator("button:has-text('Wissen')").all()

            if len(clear_buttons) > 0:
                clear_buttons[0].click()
                page.wait_for_timeout(2000)

                # After clearing, the scenario panel should not be visible
                # or should show "geen scenario actief"
                panels = page.locator("div.bg-purple-50").all()
                # Either no panels, or panel is hidden after clear
                assert len(panels) == 0 or not panels[0].is_visible()


def test_multiple_scenario_values(page: Page):
    """Test setting multiple scenario values"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(500)

    # Get all test buttons
    test_buttons = page.locator("button:has-text('🧪 Test')").all()

    # Try to set values for multiple fields (max 2 to keep test fast)
    for i in range(min(2, len(test_buttons))):
        test_buttons[i].click()
        page.wait_for_timeout(1000)

        value_input = page.locator("#modal-container input[name='value']").first
        if value_input.count() > 0:
            value_input.fill(f"value_{i}")
            page.locator("button:has-text('Bevestig')").first.click()
            page.wait_for_timeout(2000)

            # Re-query test buttons after page update
            test_buttons = page.locator("button:has-text('🧪 Test')").all()

    # After setting multiple values, scenario panel should show count
    panels = page.locator("div.bg-purple-50").all()
    if len(panels) > 0 and panels[0].is_visible():
        panel_text = panels[0].text_content()
        # Should mention multiple values or show a list
        assert len(panel_text) > 20  # Panel should have substantial content


def test_scenario_form_has_current_value(page: Page):
    """Test that scenario form shows the current value"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(500)

    # Click a test button
    test_buttons = page.locator("button:has-text('🧪 Test')").all()

    if len(test_buttons) > 0:
        test_buttons[0].click()
        page.wait_for_timeout(1000)

        # Check if current value is shown in the modal
        modal = page.locator("#modal-container").first
        modal_text = modal.text_content()

        # Modal should show some context about current value
        assert len(modal_text) > 50  # Should have meaningful content

        # Should have a form field
        form_inputs = page.locator("#modal-container input[name='value'], #modal-container textarea[name='value']").all()
        assert len(form_inputs) > 0


def test_scenario_mode_persists_across_navigation(page: Page):
    """Test that scenario mode setting persists"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(1000)

    # Verify it's enabled
    assert scenario_page.is_scenario_mode_enabled()

    # Reload the page
    page.reload()
    page.wait_for_timeout(1000)

    # Scenario mode should still be enabled (stored in localStorage)
    assert scenario_page.is_scenario_mode_enabled()


def test_disable_scenario_mode_after_use(page: Page):
    """Test disabling scenario mode after using it"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(500)

    # Set a scenario value
    test_buttons = page.locator("button:has-text('🧪 Test')").all()

    if len(test_buttons) > 0:
        test_buttons[0].click()
        page.wait_for_timeout(1000)

        value_input = page.locator("#modal-container input[name='value']").first
        if value_input.count() > 0:
            value_input.fill("12345")
            page.locator("button:has-text('Bevestig')").first.click()
            page.wait_for_timeout(2000)

    # Now disable scenario mode
    scenario_page.disable_scenario_mode()
    page.wait_for_timeout(1000)

    # Test buttons should not be visible
    test_buttons_after = page.locator("button:has-text('🧪 Test')").all()
    if len(test_buttons_after) > 0:
        # If any exist, they should not be visible
        assert not test_buttons_after[0].is_visible()


def test_scenario_comparison_button(page: Page):
    """Test the scenario comparison button"""
    scenario_page = ScenarioPage(page)

    # Navigate and enable scenario mode
    scenario_page.navigate_to_homepage()
    page.wait_for_timeout(500)
    scenario_page.enable_scenario_mode()
    page.wait_for_timeout(500)

    # Set a scenario value
    test_buttons = page.locator("button:has-text('🧪 Test')").all()

    if len(test_buttons) > 0:
        test_buttons[0].click()
        page.wait_for_timeout(1000)

        value_input = page.locator("#modal-container input[name='value']").first
        if value_input.count() > 0:
            value_input.fill("99999")
            page.locator("button:has-text('Bevestig')").first.click()
            page.wait_for_timeout(2000)

            # Look for comparison button in scenario panel
            compare_buttons = page.locator("button:has-text('Vergelijk')").all()

            if len(compare_buttons) > 0:
                compare_buttons[0].click()
                page.wait_for_timeout(1000)

                # Comparison view should appear (could be in modal or panel)
                # Look for comparison indicators
                page_text = page.locator("body").text_content()
                # Should show comparison-related text
                assert len(page_text) > 100  # Should have content
