import { apiRequest, ApiError, USE_MOCKS } from '@/services/apiClient';

// Mock fetch
const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

describe('apiClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('makes a successful GET request', async () => {
    const mockData = { id: 1, name: 'Test' };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce(mockData),
    });

    const result = await apiRequest('/test');
    expect(result).toEqual(mockData);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('throws ApiError for non-ok responses', async () => {
    const status = 404;
    const errorBody = { error: 'Not found' };
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status,
      text: jest.fn().mockResolvedValueOnce(JSON.stringify(errorBody)),
    });

    await expect(apiRequest('/test')).rejects.toThrow(ApiError);
  });
});
