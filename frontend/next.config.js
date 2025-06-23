/** @type {import('next').NextConfig} */
const nextConfig = {
  /* config options here */
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
      {
        source: '/api/video/:path*',
        destination: 'http://localhost:8000/api/youtube/:path*',
      },
      {
        source: '/api/subtitle/:path*',
        destination: 'http://localhost:8000/api/subtitle/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
