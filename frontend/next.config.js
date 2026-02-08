/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'img.youtube.com',
      },
      {
        protocol: 'https',
        hostname: 'i.ytimg.com',
      },
    ],
  },
  eslint: {
    // O repo tem regras de ESLint bem estritas e várias páginas antigas falham no lint.
    // Para não quebrar builds (incluindo Docker), ignoramos o lint durante `next build`.
    // O lint continua disponível via `npm run lint`.
    ignoreDuringBuilds: true,
  },
}

module.exports = nextConfig
