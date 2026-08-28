const http = require('http');

const server = http.createServer((req, res) => {
  if (req.method === 'POST' && req.url === '/api/score') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      console.log('score payload:', body);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok' }));
    });
    return;
  }
  res.writeHead(404);
  res.end();
});

server.listen(3000, () => console.log('Mock backend on :3000'));
