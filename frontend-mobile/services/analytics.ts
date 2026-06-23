/**
 * Analytics tracking service
 * 
 * This service provides a simple interface for tracking events.
 * Connect to your analytics provider (Google Analytics, Plausible, etc.)
 * by implementing the trackEvent function.
 */

type AnalyticsEvent =
  | { type: "page_view"; page: string }
  | { type: "cta_click"; cta: "primary" | "secondary"; location: string }
  | { type: "scroll_depth"; depth: number }
  | { type: "benchmark_load"; status: "success" | "error"; duration?: number }
  | { type: "faq_expand"; question: string }
  | { type: "error"; error: string; context?: string };

/**
 * Track an analytics event
 * 
 * TODO: Connect to your analytics provider
 * Example implementations:
 * - Google Analytics: gtag('event', event.type, { ...event })
 * - Plausible: plausible(event.type, { props: event })
 * - Custom: Send to your analytics backend
 */
export function trackEvent(event: AnalyticsEvent): void {
  // Development mode: log to console
  if (__DEV__) {
    console.log("[Analytics]", event);
    return;
  }

  // Production: Send to analytics provider
  // TODO: Implement your analytics provider integration here
}

/**
 * Track page view
 */
export function trackPageView(page: string): void {
  trackEvent({ type: "page_view", page });
}

/**
 * Track CTA click
 */
export function trackCTAClick(cta: "primary" | "secondary", location: string): void {
  trackEvent({ type: "cta_click", cta, location });
}

/**
 * Track scroll depth (percentage of page scrolled)
 */
export function trackScrollDepth(depth: number): void {
  trackEvent({ type: "scroll_depth", depth });
}

/**
 * Track benchmark data load
 */
export function trackBenchmarkLoad(status: "success" | "error", duration?: number): void {
  trackEvent({ type: "benchmark_load", status, duration });
}

/**
 * Track FAQ expansion
 */
export function trackFAQExpand(question: string): void {
  trackEvent({ type: "faq_expand", question });
}

/**
 * Track error
 */
export function trackError(error: string, context?: string): void {
  trackEvent({ type: "error", error, context });
}
