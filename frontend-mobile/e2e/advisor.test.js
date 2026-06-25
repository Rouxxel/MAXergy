const { reloadApp } = require('detox-expo-helpers');

describe('Advisor Flow', () => {
  beforeAll(async () => {
    await reloadApp();
  });

  it('should show advisor page', async () => {
    await element(by.id('advisor-tab')).tap();
    await expect(element(by.id('advisor-page'))).toBeVisible();
  });
});
