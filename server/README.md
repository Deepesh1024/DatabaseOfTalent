# DOT Registration Server (Local Development)

This small Express server provides a secure server-side endpoint to accept registration submissions and insert them into Supabase using a server-side key.

## Setup

1. Copy `.env.example` to `.env` and set your Supabase service key (use a service_role or a server key, not exposed to browsers):

   SUPABASE_URL=https://eorwvuivppmyzavvuquo.supabase.co
   SUPABASE_KEY=your-safe-server-key
   PORT=3000

2. Install dependencies:

   cd server
   npm install

3. Run the server:

   npm run dev    # if you have nodemon
   npm start      # production mode

The server listens on `http://localhost:3000` by default and exposes `POST /register`.

## Endpoint

POST /register
- Content-Type: application/json
- Body: { full_name, personal_email, company_name, company_email, accepted_terms, newsletter_opt_in }

Returns JSON: { success: true, data: [...] } on success or { success: false, error: "message" } on error.

## Security Notes
- Do NOT commit your `SUPABASE_KEY` or database passwords to source control or client code.
- Rotate any keys or DB credentials if they were shared in public places.
- For production deploy using environment variables in a secure platform (VPS, serverless, or container secrets manager).

