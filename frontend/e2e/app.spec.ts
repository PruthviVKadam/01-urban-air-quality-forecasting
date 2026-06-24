import { test, expect } from "@playwright/test";

test.describe("Urban Air Quality Forecasting - e2e", () => {
  test("should render the map and allow scrubbing", async ({ page }) => {
    await page.goto("/");

    // Expect the title to be present
    await expect(page).toHaveTitle(/Atmosphere/i);

    // Expect the map container to be present
    const mapContainer = page.locator(".maplibregl-map");
    await expect(mapContainer).toBeVisible({ timeout: 10000 });

    // Expect markers to exist
    const markers = page.locator(".maplibregl-marker");
    await expect(markers.first()).toBeVisible({ timeout: 10000 });

    // Scrub the horizon
    const scrubber = page.locator("input[type='range']");
    await expect(scrubber).toBeVisible();

    // The live value is 'Now' -> 0
    await expect(scrubber).toHaveValue("0");

    // Change scrubber value to 12
    await scrubber.fill("12");
    await expect(scrubber).toHaveValue("12");

    // Check Pollutant Toggle
    const toggleO3 = page.locator("button:has-text('O₃')");
    await toggleO3.click();
    await expect(toggleO3).toHaveAttribute("aria-pressed", "true");

    // Test Play button
    const playButton = page.getByRole("button", { name: /play/i });
    if (await playButton.isVisible()) {
      await playButton.click();
      // Should auto increment
      await page.waitForTimeout(500);
      const val = parseInt(await scrubber.inputValue(), 10);
      expect(val).toBeGreaterThan(12);
    }
  });
});
