const http = require('http');

const webPort = Number(process.env.WEB_PORT || '3200');
const nextPort = Number(process.env.NEXT_INTERNAL_PORT || '3201');
const apiPort = Number(process.env.API_PORT || '8200');

function proxy(req, res, targetPort) {
  const options = {
    hostname: '127.0.0.1',
    port: targetPort,
    path: req.url,
    method: req.method,
    headers: {
      ...req.headers,
      host: `127.0.0.1:${targetPort}`,
      'x-forwarded-host': req.headers.host || '',
      'x-forwarded-proto': 'http',
    },
  };

  const upstream = http.request(options, (upstreamRes) => {
    res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
    upstreamRes.pipe(res);
  });

  upstream.on('error', (error) => {
    res.writeHead(502, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ error: 'upstream_unavailable', detail: error.message }));
  });

  req.pipe(upstream);
}

const server = http.createServer((req, res) => {
  if ((req.url || '').startsWith('/api/')) {
    return proxy(req, res, apiPort);
  }
  return proxy(req, res, nextPort);
});

server.listen(webPort, '0.0.0.0', () => {
  console.log(`PlumbPrice proxy listening on 0.0.0.0:${webPort}`);
});
