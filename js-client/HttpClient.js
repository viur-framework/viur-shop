class HTTPError extends Error {
    constructor(code, statusText, message, response) {
        super(message || statusText);
        if (arguments.length >= 4 && response) {
            Object.assign(this, response);
        }
        this.statusText = statusText;
        this.statusCode = code;
        this.response = response;
    }
}

/**
 * Wrapper for fetch.
 * Inspired by https://kentcdodds.com/blog/replace-axios-with-a-simple-custom-fetch-wrapper
 *
 * @param {String} url The url of the ressource to fetch.
 * @param {Object=} json Optional. Data used as json-serialized payload.
 * @param {String=} method Optional. The HTTP method, e.g. POST. Default: GET (if json is unset).
 * @param {Object=} params Optional. Params used as body for POST and get-query-String for others.
 * @param {Object=} customConfig Some custom values for the fetch call.
 * @returns {Promise<Response>} Returns the raw request a promise, or throws a HTTPError.
 */
function request(url, {json, method, params, ...customConfig} = {}) {
    if (!method) {
        method = json ? 'POST' : 'GET'
    }
    const config = {
        method: method,
        headers: {
            'X-Requested-With': 'Fetch',
            ...customConfig.headers,
        },
        ...customConfig,
    }
    if (json) {
        config.body = JSON.stringify(json);
        config.headers['Content-Type'] = 'application/json';
    } else if (params && method === 'POST') {
        if (typeof params === 'string' || params instanceof String) {
            // provided a query string, e.g.: foo=1&bar=2
            config.body = new URLSearchParams(params);
        } else if (params instanceof HTMLFormElement) {
            // provided a HTML form element
            config.body = new FormData(params);
        } else {
            // provided a object, e.g.: {foo: 1, bar: 2, baz: [3, 4]}
            config.body = new FormData();
            Object.entries(params).forEach(([key, value]) => {
                if (Array.isArray(value)) {
                    for (const val of value) {
                        config.body.append(key, val)
                    }
                } else {
                    config.body.append(key, value)
                }
            });
        }
    }
    if (params && (method === 'GET' || json)) {
        const getParams = new URLSearchParams(params)
        url += `?${getParams.toString()}`;
    }
    return window
        .fetch(url, config)
        .then(async response => {
            if (response.ok) {
                return response
            } else {
                const errorMessage = `${response.status} ${response.statusText}: ${response.headers.get('x-viur-error')}`
                return Promise.reject(new HTTPError(response.status, response.statusText, errorMessage, response))
            }
        })
}

/**
 * Return a new skey.
 * @returns {Promise<String>} The resolved json-Promise (the skey).
 */
function getSkey() {
    return request('/json/skey')
        .then(request => request.json())
}

/**
 * Shows a alert with an error-message.
 * @param {any} error The exception. Could be an instance of HTTPError or any other error/value.
 */
function errorHandler(error) {
    console.error(error);
    let headline = `Error`;
    if (error instanceof HTTPError) {
        headline += ` ${error.statusCode} ${error.statusText}`;
    }
    alert(
        `Sorry, an unexpected error occurred.
${headline}
${error}
Please try again our contact our customer service.`,
    )
}

export {HTTPError, request, getSkey, errorHandler};
