import type { Metadata } from "next";
import { KnowledgeVaultView } from "@/components/modules/knowledge-vault/knowledge-vault-view";

export const metadata: Metadata = { title: "Knowledge Vault" };

export default function KnowledgeVaultPage() {
  return <KnowledgeVaultView />;
}
