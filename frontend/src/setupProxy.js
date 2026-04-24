const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

  app.use(
    ['/api', '/media'],
    createProxyMiddleware({
      target: backendUrl,
      changeOrigin: true,
    })
  );
};
