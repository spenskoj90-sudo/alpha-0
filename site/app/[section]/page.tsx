import { notFound } from 'next/navigation';
import { publicSections } from '../components/public-sections';
import PublicSectionPage from './content';

export const dynamicParams = false;
export function generateStaticParams() { return publicSections.map(({ path }) => ({ section: path })); }
export async function generateMetadata({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  const entry = publicSections.find(item => item.path === section);
  return { title: entry?.en ?? 'Page not found' };
}
export default async function Section({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  const entry = publicSections.find(item => item.path === section);
  if (!entry) notFound();
  return <PublicSectionPage section={entry.path} />;
}
