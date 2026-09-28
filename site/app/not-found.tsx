import Link from "next/link";
import { PublicFooter } from "./components/public-footer";
import { PublicHeader } from "./components/public-header";

export default function NotFound() {
  return (
    <>
      <PublicHeader />
      <main className="document-main">
        <div className="site-shell document-shell">
          <div className="eyebrow">404</div>
          <h1>Surface not found.</h1>
          <p className="document-lead">The requested public SENTINEL page does not exist.</p>
          <Link className="button-primary inline-button" href="/">Return home</Link>
        </div>
      </main>
      <PublicFooter />
    </>
  );
}
