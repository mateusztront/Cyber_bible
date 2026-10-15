// Cyber Bible - keeps the Eel connection alive (load after eel.js, before script.js)
//
// Phones close the page's websocket when you switch apps or lock the screen,
// and eel.js never reconnects: later calls go into the closed socket, are
// silently dropped, and the awaited promise never settles, so buttons seem to
// do nothing. This reconnects on demand, fails calls whose reply can no longer
// arrive, gives every call a timeout and shows the connection state.

(function() {
    // The server runs one call at a time, so a call can wait behind a long
    // publish or Midjourney job. These catch replies that never come; they are
    // not expected durations.
    const CALL_TIMEOUT_MS = 5 * 60 * 1000;
    const CALL_TIMEOUT_OVERRIDES_MS = { publish: 15 * 60 * 1000 };
    const RETRY_DELAY_MS = 3000;
    // After this long in the background, a socket that still looks open may
    // already be cut off, so it's replaced if nothing is waiting on it.
    const STALE_AFTER_HIDDEN_MS = 30 * 1000;
    // Calls the page makes on its own, which shouldn't keep a stale socket alive.
    const BACKGROUND_CALLS = new Set(['check_2fa_needed', 'client_log']);

    let disconnectedSince = null;
    let failedCalls = 0;
    let retryTimer = null;
    let hiddenAt = null;

    function connectionLost() {
        return new Error('Lost connection to the server');
    }

    // Every call gets a timeout, and its callback entry is removed once it
    // settles (eel.js keeps them forever), so pending entries = waiting calls.
    const originalCallReturn = eel._call_return;
    eel._call_return = function(call) {
        const register = originalCallReturn(call);
        return function(callback = null) {
            const result = register(callback);
            const entry = eel._call_return_callbacks[call.call];
            const timeoutMs = CALL_TIMEOUT_OVERRIDES_MS[call.name] || CALL_TIMEOUT_MS;
            const timer = setTimeout(() => {
                console.warn(`No reply to ${call.name} after ${timeoutMs / 1000}s`);
                entry.reject(new Error(`No reply from the server to ${call.name}`));
            }, timeoutMs);
            const settle = fn => value => {
                clearTimeout(timer);
                delete eel._call_return_callbacks[call.call];
                if (fn) fn(value);
            };
            entry.name = call.name;
            entry.resolve = settle(entry.resolve);
            entry.reject = settle(entry.reject);
            return result;
        };
    };

    // Send only on an open socket; otherwise queue the call (eel.js sends its
    // queue when a socket opens) and reconnect.
    eel._import_py_function = function(name) {
        eel[name] = function() {
            const call = eel._call_object(name, arguments);
            const ws = eel._websocket;
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(eel._toJSON(call));
            } else {
                eel._mock_queue.push(call);
                reconnect();
            }
            return eel._call_return(call);
        };
    };

    function waitingCalls() {
        return Object.values(eel._call_return_callbacks).filter(e => !BACKGROUND_CALLS.has(e.name));
    }

    function failPendingCalls() {
        // Replies to calls sent on a dead socket never come on a new one.
        // Queued calls are dropped too, so a publish that already showed as
        // failed can't go out later by surprise.
        const pending = Object.values(eel._call_return_callbacks);
        eel._mock_queue.length = 0;
        pending.forEach(entry => entry.reject(connectionLost()));
        failedCalls += pending.filter(e => !BACKGROUND_CALLS.has(e.name)).length;
    }

    function watch(ws) {
        ws.addEventListener('open', onOpen);
        ws.addEventListener('close', onClose);
    }

    function openSocket(old) {
        const ws = new WebSocket(old.url);
        ws.onopen = old.onopen;       // eel.js: re-imports functions, sends the queue
        ws.onmessage = old.onmessage; // eel.js: resolves calls, runs exposed JS
        watch(ws);
        eel._websocket = ws;
    }

    function reconnect() {
        clearTimeout(retryTimer);
        const ws = eel._websocket;
        if (!ws) return; // eel.js hasn't opened its first socket yet
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) return;
        openSocket(ws);
    }

    function onOpen(event) {
        if (event.target !== eel._websocket) return;
        if (disconnectedSince !== null) {
            const seconds = Math.round((Date.now() - disconnectedSince) / 1000);
            eel.client_log(`reconnected after ${seconds}s offline, ${failedCalls} unanswered call(s) failed`);
            disconnectedSince = null;
            failedCalls = 0;
        }
        showState(true);
    }

    function onClose(event) {
        if (event.target !== eel._websocket) return; // a socket we already replaced
        if (disconnectedSince === null) disconnectedSince = Date.now();
        failPendingCalls();
        showState(false);
        clearTimeout(retryTimer);
        if (!document.hidden) retryTimer = setTimeout(reconnect, RETRY_DELAY_MS);
    }

    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            hiddenAt = Date.now();
            return;
        }
        const ws = eel._websocket;
        const wasAway = hiddenAt !== null && Date.now() - hiddenAt > STALE_AFTER_HIDDEN_MS;
        hiddenAt = null;
        if (wasAway && ws && ws.readyState === WebSocket.OPEN && waitingCalls().length === 0) {
            failPendingCalls(); // only background calls are left
            openSocket(ws);
            ws.close();
        } else {
            reconnect();
        }
    });
    window.addEventListener('online', reconnect);
    window.addEventListener('pageshow', reconnect); // back/forward cache restore

    // eel.js opens the first socket on DOMContentLoaded; this listener is
    // registered after its one, so the socket exists by now.
    document.addEventListener('DOMContentLoaded', function() {
        if (eel._websocket) watch(eel._websocket);
    });

    // Badge in the corner; shown only if the connection stays down for a moment,
    // so a quick reconnect doesn't flash it.
    let badgeTimer = null;
    function showState(online) {
        const badge = document.getElementById('connection-status');
        if (!badge) return;
        if (online) {
            clearTimeout(badgeTimer);
            badgeTimer = null;
            badge.hidden = true;
        } else if (badgeTimer === null && badge.hidden) {
            // Not restarted by each failed retry, or it would never show
            badgeTimer = setTimeout(() => {
                badgeTimer = null;
                badge.hidden = false;
            }, 1000);
        }
    }
})();
