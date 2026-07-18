import { redirect } from "next/navigation";

export default function HomePage() {
  // Root redirects to marketing page
  redirect("/marketing");
}
