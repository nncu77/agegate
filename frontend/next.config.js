/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The backend lives on a different origin (Railway). We don't proxy
  // through Next.js because that would route image bytes through a
  // Vercel edge → Railway hop, adding latency to a latency-sensitive flow.
  // The browser talks to the backend directly via NEXT_PUBLIC_API_URL.
  poweredByHeader: false,
};

module.exports = nextConfig;
