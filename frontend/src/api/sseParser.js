/**
 * SSE Stream Parser for POST-based Server-Sent Events.
 *
 * Since the browser's native EventSource only supports GET,
 * we use fetch() + ReadableStream to parse SSE from a POST response.
 *
 * SSE Format (per chat.py):
 *   event: <event_name>\n
 *   data: <json_string>\n
 *   \n
 *
 * Event types: agent_start, token, agent_end, state_update,
 *              requires_approval, error, done
 */

/**
 * Parse an SSE stream from a fetch Response and invoke callbacks.
 *
 * @param {Response} response — The fetch Response with Content-Type: text/event-stream
 * @param {Object} handlers — Callback map keyed by event name
 * @param {Function} [handlers.agent_start]       — ({agent}) => void
 * @param {Function} [handlers.token]             — ({content}) => void
 * @param {Function} [handlers.agent_end]         — ({agent}) => void
 * @param {Function} [handlers.state_update]      — ({current_topic, quiz_score, completed_topics, is_certified}) => void
 * @param {Function} [handlers.requires_approval] — ({message, pending_node}) => void
 * @param {Function} [handlers.error]             — ({detail}) => void
 * @param {Function} [handlers.done]              — ({}) => void
 */
export async function parseSSEStream(response, handlers) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Normalize \r\n to \n (sse-starlette on Windows sends \r\n)
      buffer = buffer.replace(/\r\n/g, '\n');

      // SSE messages are separated by double newlines
      const messages = buffer.split('\n\n');
      // Keep the last chunk in buffer (it may be incomplete)
      buffer = messages.pop() || '';

      for (const message of messages) {
        if (!message.trim()) continue;

        let eventName = 'message';
        let eventData = '';

        for (const line of message.split('\n')) {
          if (line.startsWith('event:')) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            // BUG-10 FIX: Accumulate multi-line data per SSE spec
            const chunk = line.slice(5).trim();
            eventData = eventData ? eventData + '\n' + chunk : chunk;
          }
        }

        // Parse the JSON data
        let parsedData = {};
        if (eventData) {
          try {
            parsedData = JSON.parse(eventData);
          } catch {
            // If it's not JSON, wrap it as content
            parsedData = { content: eventData };
          }
        }

        // Invoke the handler for this event type
        const handler = handlers[eventName];
        if (handler) {
          handler(parsedData);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
