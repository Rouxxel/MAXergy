const { reloadApp } = require('detox-expo-helpers');

describe('Results Flow', () => {
  beforeAll(async () => {
    await reloadApp();
  });

  it('should show results page', async () => {
    await expect(element(by.id('results-page'))).toBeVisible();
  });
});
