# happyrenewal
set -euo pipefail

# 1) Scaffold Next.js (TypeScript, Tailwind, App Router) into the current empty repo
npx create-next-app@latest . --ts --eslint --tailwind --app --src-dir --use-npm --no-git

# 2) Dependencies
npm i prisma @prisma/client next-auth @auth/prisma-adapter zod date-fns
npm i -D tsx

# 3) Prisma init
npx prisma init

# 4) Set .env DATABASE_URL from Neon (paste when prompted)
printf "\nPaste your Neon DATABASE_URL and press Enter:\n"
read -r NEON_URL
sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$NEON_URL|" .env

# Example env file
cat > .env.example <<'ENVEX'
DATABASE_URL=postgres://user:pass@host/db?sslmode=require
NEXTAUTH_SECRET=replace_with_32+_char_secret
DEV_ADMIN_PASSWORD=replace_with_temp_password
ENVEX

# 5) Prisma schema
cat > prisma/schema.prisma <<'PRISMA'
generator client { provider = "prisma-client-js" }

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id            String    @id @default(cuid())
  name          String?
  email         String?   @unique
  emailVerified DateTime?
  image         String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  accounts      Account[]
  licenses      License[]
}

model Account {
  id                String  @id @default(cuid())
  userId            String
  type              String
  provider          String
  providerAccountId String
  refresh_token     String?
  access_token      String?
  expires_at        Int?
  token_type        String?
  scope             String?
  id_token          String?
  session_state     String?
  user User @relation(fields: [userId], references: [id], onDelete: Cascade)
  @@unique([provider, providerAccountId])
}

model VerificationToken {
  identifier String
  token      String @unique
  expires    DateTime
  @@unique([identifier, token])
}

model Vendor {
  id        String   @id @default(cuid())
  name      String   @unique
  website   String?
  fyeMonth  Int
  createdAt DateTime @default(now())
  licenses  License[]
}

model License {
  id                   String    @id @default(cuid())
  userId               String
  vendorId             String
  productName          String
  seats                Int?
  termStart            DateTime
  termEnd              DateTime
  renewalWindowDays    Int       @default(60)
  notes                String?
  createdAt            DateTime  @default(now())
  updatedAt            DateTime  @updatedAt
  user   User   @relation(fields: [userId], references: [id], onDelete: Cascade)
  vendor Vendor @relation(fields: [vendorId], references: [id], onDelete: Restrict)
  messages RenewalMessage[]
}

enum RenewalStatus { PENDING SCHEDULED SENT FAILED CANCELLED }
enum Channel { EMAIL }

model RenewalMessage {
  id             String         @id @default(cuid())
  licenseId      String
  scheduledFor   DateTime
  status         RenewalStatus  @default(PENDING)
  sentAt         DateTime?
  channel        Channel        @default(EMAIL)
  messagePreview String?
  createdAt      DateTime       @default(now())
  updatedAt      DateTime       @updatedAt
  license License @relation(fields: [licenseId], references: [id], onDelete: Cascade)
}
PRISMA

# 6) Seed major vendors
cat > prisma/seed.ts <<'SEED'
import { PrismaClient } from "@prisma/client";
const prisma = new PrismaClient();
const vendors = [
  { name: "Microsoft", website: "https://microsoft.com", fyeMonth: 6 },
  { name: "Adobe", website: "https://adobe.com", fyeMonth: 11 },
  { name: "Salesforce", website: "https://salesforce.com", fyeMonth: 1 },
  { name: "SAP", website: "https://sap.com", fyeMonth: 12 },
  { name: "Oracle", website: "https://oracle.com", fyeMonth: 5 },
  { name: "ServiceNow", website: "https://servicenow.com", fyeMonth: 1 },
  { name: "Workday", website: "https://workday.com", fyeMonth: 1 },
  { name: "Atlassian", website: "https://atlassian.com", fyeMonth: 6 },
  { name: "Cisco", website: "https://cisco.com", fyeMonth: 7 },
  { name: "Zoom", website: "https://zoom.us", fyeMonth: 1 },
  { name: "Okta", website: "https://okta.com", fyeMonth: 1 },
  { name: "Datadog", website: "https://datadoghq.com", fyeMonth: 12 },
  { name: "Snowflake", website: "https://snowflake.com", fyeMonth: 1 },
  { name: "MongoDB", website: "https://mongodb.com", fyeMonth: 1 },
  { name: "Google Cloud", website: "https://cloud.google.com", fyeMonth: 12 },
  { name: "AWS", website: "https://aws.amazon.com", fyeMonth: 12 },
  { name: "GitHub", website: "https://github.com", fyeMonth: 6 },
  { name: "HashiCorp", website: "https://hashicorp.com", fyeMonth: 1 },
  { name: "Elastic", website: "https://elastic.co", fyeMonth: 4 },
  { name: "Miro", website: "https://miro.com", fyeMonth: 12 },
  { name: "Figma", website: "https://figma.com", fyeMonth: 1 },
  { name: "Slack", website: "https://slack.com", fyeMonth: 1 },
  { name: "Box", website: "https://box.com", fyeMonth: 1 },
  { name: "Dropbox", website: "https://dropbox.com", fyeMonth: 12 },
  { name: "Zendesk", website: "https://zendesk.com", fyeMonth: 12 },
  { name: "HubSpot", website: "https://hubspot.com", fyeMonth: 12 },
  { name: "JFrog", website: "https://jfrog.com", fyeMonth: 12 },
  { name: "CrowdStrike", website: "https://crowdstrike.com", fyeMonth: 1 },
  { name: "Palo Alto Networks", website: "https://paloaltonetworks.com", fyeMonth: 7 },
  { name: "Fortinet", website: "https://fortinet.com", fyeMonth: 12 },
];
async function main() {
  for (const v of vendors) {
    await prisma.vendor.upsert({
      where: { name: v.name },
      update: { website: v.website, fyeMonth: v.fyeMonth },
      create: { name: v.name, website: v.website, fyeMonth: v.fyeMonth },
    });
  }
}
main().then(async () => {
  await prisma.$disconnect();
  console.log(`Seeded ${vendors.length} vendors`);
}).catch(async (e) => {
  console.error(e);
  await prisma.$disconnect();
  process.exit(1);
});
SEED

# 7) Prisma client + DB sync + seed
npx prisma generate
npx prisma db push
# add seed script before running it
node - <<'NODE'
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('package.json','utf8'));
pkg.scripts = {
  ...pkg.scripts,
  "seed": "tsx prisma/seed.ts",
  "db:migrate": "prisma migrate deploy",
  "db:push": "prisma db push",
  "build": "prisma migrate deploy && next build"
};
fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
NODE
npm run seed

# 8) Prisma client helper
mkdir -p src/lib
cat > src/lib/prisma.ts <<'TS'
import { PrismaClient } from "@prisma/client";
const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };
export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["query", "error", "warn"] : ["error"],
  });
if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;
TS

# 9) Auth (email links logged to console) + temp credentials login
mkdir -p src/app/api/auth/[...nextauth]
cat > src/app/api/auth/[...nextauth]/route.ts <<'TS'
import NextAuth from "next-auth";
import { PrismaAdapter } from "@auth/prisma-adapter";
import { prisma } from "@/lib/prisma";
import EmailProvider from "next-auth/providers/email";
import Credentials from "next-auth/providers/credentials";
import { z } from "zod";

const handler = NextAuth({
  adapter: PrismaAdapter(prisma),
  secret: process.env.NEXTAUTH_SECRET,
  session: { strategy: "jwt" },
  providers: [
    EmailProvider({
      from: process.env.EMAIL_FROM || "noreply@localhost",
      async sendVerificationRequest({ url, identifier }) {
        console.log("Login link for", identifier, "=>", url);
      },
    }),
    Credentials({
      name: "Temporary login",
      credentials: { email: { label: "Email", type: "text" }, password: { label: "Password", type: "password" } },
      async authorize(creds) {
        const schema = z.object({ email: z.string().email(), password: z.string().min(6) });
        const parsed = schema.safeParse(creds);
        if (!parsed.success) return null;
        if (!process.env.DEV_ADMIN_PASSWORD || parsed.data.password !== process.env.DEV_ADMIN_PASSWORD) return null;
        const user = await prisma.user.upsert({
          where: { email: parsed.data.email },
          update: {},
          create: { email: parsed.data.email, name: parsed.data.email.split("@")[0] },
        });
        return { id: user.id, email: user.email ?? undefined, name: user.name ?? undefined };
      },
    }),
  ],
});
export { handler as GET, handler as POST };
TS

# 10) Cron endpoint
mkdir -p src/app/api/cron/renewals
cat > src/app/api/cron/renewals/route.ts <<'TS'
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { addDays, isBefore } from "date-fns";

function monthName(m: number) {
  return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m-1] ?? String(m);
}

export async function GET(req: NextRequest) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("x-cron-secret") !== secret) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }
  const today = new Date();
  const licenses = await prisma.license.findMany({ include: { vendor: true } });

  let created = 0;
  for (const lic of licenses) {
    const leadDays = lic.renewalWindowDays ?? 60;
    const windowStart = addDays(lic.termEnd, -leadDays);
    const fyeMonth = lic.vendor.fyeMonth;
    const ninetyDaysOut = addDays(today, 90);
    const fyeDateThisYear = new Date(today.getFullYear(), fyeMonth - 1, 1);
    const fyeInWindow = isBefore(today, ninetyDaysOut) &&
      (fyeDateThisYear >= today && fyeDateThisYear <= ninetyDaysOut);
    const dueSoon = today >= windowStart && today <= lic.termEnd;
    if (!dueSoon && !fyeInWindow) continue;
    const scheduledFor = dueSoon ? today : fyeDateThisYear;
    await prisma.renewalMessage.create({
      data: {
        licenseId: lic.id,
        scheduledFor,
        status: "PENDING",
        channel: "EMAIL",
        messagePreview: `Renewal prep: ${lic.productName} (${lic.vendor.name}) ends ${lic.termEnd.toISOString().slice(0,10)}. Vendor FYE: ${monthName(fyeMonth)}.`,
      },
    });
    created++;
  }
  return NextResponse.json({ ok: true, created });
}
TS

# 11) Minimal layout + home
cat > src/app/layout.tsx <<'TSX'
import "./globals.css";
import { ReactNode } from "react";
export const metadata = {
  title: "HappyRenewal",
  description: "License renewals optimized by fiscal calendars",
};
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}
TSX

cat > src/app/page.tsx <<'TSX'
import Link from "next/link";
export default function Home() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-3xl font-bold">HappyRenewal</h1>
      <p className="mt-2 text-gray-600">
        Track licenses, get renewal prompts aligned with vendor fiscal year ends.
      </p>
      <div className="mt-6 space-x-4">
        <Link className="underline" href="/api/auth/signin">Sign in</Link>
      </div>
    </main>
  );
}
TSX

# 12) Commit & push
git config user.name "happyrenewal-bot"
git config user.email "actions@users.noreply.github.com"
git add -A
git commit -m "feat: bootstrap app, prisma schema, seed, auth, cron"
git branch -M main
git push -u origin main
