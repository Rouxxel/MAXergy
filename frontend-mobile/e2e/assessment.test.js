const { reloadApp } = require('detox-expo-helpers');

describe('Assessment Flow', () => {
  beforeAll(async () => {
    await reloadApp();
  });

  it('should navigate to assessment page', async () => {
    await element(by.id('start-assessment-btn')).tap();
    await expect(element(by.id('assessment-page'))).toBeVisible();
  });
});
