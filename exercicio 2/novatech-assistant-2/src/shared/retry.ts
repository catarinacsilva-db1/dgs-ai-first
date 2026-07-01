export interface RetryContext {
  attempt: number;
  maxAttempts: number;
  delayMs: number;
}

export interface RetryOptions {
  maxAttempts?: number;
  initialDelayMs?: number;
  backoffMultiplier?: number;
  shouldRetry?: (error: unknown, context: RetryContext) => boolean;
  onRetry?: (error: unknown, context: RetryContext) => void;
  sleep?: (ms: number) => Promise<void>;
}

const DEFAULT_MAX_ATTEMPTS = 3;
const DEFAULT_INITIAL_DELAY_MS = 200;
const DEFAULT_BACKOFF_MULTIPLIER = 2;

interface RetryRuntimeConfig {
  maxAttempts: number;
  initialDelayMs: number;
  backoffMultiplier: number;
  shouldRetry?: (error: unknown, context: RetryContext) => boolean;
  onRetry?: (error: unknown, context: RetryContext) => void;
  sleep: (ms: number) => Promise<void>;
}

function defaultSleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function buildConfig(options: RetryOptions): RetryRuntimeConfig {
  const config: RetryRuntimeConfig = {
    maxAttempts: options.maxAttempts ?? DEFAULT_MAX_ATTEMPTS,
    initialDelayMs: options.initialDelayMs ?? DEFAULT_INITIAL_DELAY_MS,
    backoffMultiplier: options.backoffMultiplier ?? DEFAULT_BACKOFF_MULTIPLIER,
    shouldRetry: options.shouldRetry,
    onRetry: options.onRetry,
    sleep: options.sleep ?? defaultSleep,
  };

  validateConfig(config);

  return config;
}

function validateConfig(config: RetryRuntimeConfig): void {
  if (!Number.isInteger(config.maxAttempts) || config.maxAttempts < 1) {
    throw new Error("maxAttempts must be an integer greater than 0.");
  }

  if (config.initialDelayMs < 0) {
    throw new Error("initialDelayMs must be greater than or equal to 0.");
  }

  if (config.backoffMultiplier < 1) {
    throw new Error("backoffMultiplier must be greater than or equal to 1.");
  }
}

function canRetry(
  attempt: number,
  error: unknown,
  config: RetryRuntimeConfig,
  delayMs: number,
): boolean {
  if (attempt === config.maxAttempts) {
    return false;
  }

  if (!config.shouldRetry) {
    return true;
  }

  return config.shouldRetry(error, {
    attempt,
    maxAttempts: config.maxAttempts,
    delayMs,
  });
}

export async function withRetry<T>(
  operation: () => Promise<T>,
  options: RetryOptions = {},
): Promise<T> {
  const config = buildConfig(options);
  let delayMs = config.initialDelayMs;
  let lastError: unknown;

  for (let attempt = 1; attempt <= config.maxAttempts; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      if (!canRetry(attempt, error, config, delayMs)) {
        throw error;
      }

      const context: RetryContext = {
        attempt,
        maxAttempts: config.maxAttempts,
        delayMs,
      };

      config.onRetry?.(error, context);

      if (delayMs > 0) {
        await config.sleep(delayMs);
      }

      delayMs *= config.backoffMultiplier;
    }
  }

  throw lastError;
}
