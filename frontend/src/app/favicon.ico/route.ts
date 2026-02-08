export async function GET() {
  // Avoid 404 noise for browsers that request /favicon.ico by default.
  // Some Next.js/node runtimes error on Response(204) here, so return 200 with an empty icon.
  return new Response(new Uint8Array(), {
    status: 200,
    headers: {
      'Content-Type': 'image/x-icon',
      'Cache-Control': 'public, max-age=86400',
    },
  });
}

export async function HEAD() {
  return new Response(null, {
    status: 200,
    headers: {
      'Content-Type': 'image/x-icon',
      'Cache-Control': 'public, max-age=86400',
    },
  });
}
