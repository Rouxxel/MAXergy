const { reloadApp } = require('detox-expo-helpers');

describe('Landing Page', () => {
  beforeAll(async () => {
    await reloadApp();
  });

  it('should show landing page', async () => {
    await expect(element(by.id('landing-page'))).toBeVisible();
  });

  it('should have welcome text', async () => {
    await expect(element(by.text('MAXergy'))).toBeVisible();
  });
});
