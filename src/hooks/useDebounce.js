import { useState, useEffect } from 'react';

/**
 * Custom hook that delays updating a value until a specified delay has passed.
 */
export const useDebounce = (value, delay = 500) => {
    const [debouncedValue, setDebouncedValue] = useState(value);

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedValue(value);
        }, delay);

        // Cleanup: Clear timeout if the user types again before delay finishes
        return () => clearTimeout(handler);
    }, [value, delay]);

    return debouncedValue;
};