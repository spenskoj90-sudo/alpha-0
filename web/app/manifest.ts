import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'SENTINEL',
    short_name: 'SENTINEL',
    description: 'Trusted intelligence and security control plane',
    start_url: '/',
    display: 'standalone',
    background_color: '#061018',
    theme_color: '#061018',
    icons: [
      { src: '/brand/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/brand/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
  };
}
