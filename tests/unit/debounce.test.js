const debounce = require('../../src/debounce');

describe('debounce', () => {
    jest.useFakeTimers();

    it('should delay function execution', () => {
        const func = jest.fn();
        const debouncedFunc = debounce(func, 1000);

        debouncedFunc();

        // Should not be called immediately
        expect(func).not.toHaveBeenCalled();

        // Fast-forward time
        jest.advanceTimersByTime(1000);

        // Should be called now
        expect(func).toHaveBeenCalled();
    });

    it('should execute only once for multiple calls within wait time', () => {
        const func = jest.fn();
        const debouncedFunc = debounce(func, 1000);

        debouncedFunc();
        debouncedFunc();
        debouncedFunc();

        jest.advanceTimersByTime(1000);

        expect(func).toHaveBeenCalledTimes(1);
    });
});
