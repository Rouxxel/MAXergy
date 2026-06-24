import {
  trackEvent,
  trackPageView,
  trackCTAClick,
  trackScrollDepth,
  trackBenchmarkLoad,
  trackFAQExpand,
  trackError,
} from '@/services/analytics';

// Mock console.log
const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});

// Set __DEV__ to true for testing
(global as any).__DEV__ = true;

describe('analytics service', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('logs page view event', () => {
    const testPage = '/test-page';
    trackPageView(testPage);
    expect(consoleLogSpy).toHaveBeenCalledWith("[Analytics]", { type: "page_view", page: testPage });
  });

  it('logs CTA click event', () => {
    trackCTAClick('primary', 'hero');
    expect(consoleLogSpy).toHaveBeenCalledWith("[Analytics]", { type: "cta_click", cta: "primary", location: "hero" });
  });

  it('logs scroll depth event', () => {
    trackScrollDepth(50);
    expect(consoleLogSpy).toHaveBeenCalledWith("[Analytics]", { type: "scroll_depth", depth: 50 });
  });

  it('logs FAQ expand event', () => {
    const testQuestion = 'Test question?';
    trackFAQExpand(testQuestion);
    expect(consoleLogSpy).toHaveBeenCalledWith("[Analytics]", { type: "faq_expand", question: testQuestion });
  });

  it('logs error event', () => {
    trackError('Test error', 'test context');
    expect(consoleLogSpy).toHaveBeenCalledWith("[Analytics]", { type: "error", error: "Test error", context: "test context" });
  });
});
