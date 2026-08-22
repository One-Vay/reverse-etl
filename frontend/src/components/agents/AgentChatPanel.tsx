import { MessageCircle, Send } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Textarea } from "@/components/ui/Textarea";
import { useAgentMessages, useSendAgentMessage } from "@/hooks/useAgents";
import { cn, formatDateTime } from "@/lib/utils";

interface AgentChatPanelProps {
  agentId: number;
}

/** Ask this specific agent questions ("why does this lead show no
 * name?", "how do I fix it?") and get answers grounded in its own goal,
 * plan, mapping, and last run — read-only by design: the assistant tells
 * the user what to change, it never changes the agent's configuration
 * itself, so nothing about the agent's behavior is hidden or silently
 * mutated by a chat message. */
export function AgentChatPanel({ agentId }: AgentChatPanelProps) {
  const messagesQuery = useAgentMessages(agentId);
  const sendMessage = useSendAgentMessage(agentId);
  const [draft, setDraft] = useState("");

  const messages = messagesQuery.data ?? [];

  const handleSend = async () => {
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    try {
      await sendMessage.mutateAsync(text);
    } catch {
      // Already surfaced via the mutation's onError toast; restore the
      // draft so the user doesn't lose what they typed.
      setDraft(text);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-muted-foreground">
        Ask this agent about its data, its plan, or why a run turned out the way
        it did. It can only answer and suggest — it won't change any settings on
        its own.
      </p>

      <div className="flex max-h-80 flex-col gap-3 overflow-y-auto scrollbar-thin rounded-md border border-border p-3">
        {messagesQuery.isLoading ? (
          <p className="text-xs text-muted-foreground">Loading…</p>
        ) : messages.length === 0 ? (
          <EmptyState
            icon={MessageCircle}
            title="No messages yet"
            description='Ask something like "why does this lead show no name?"'
          />
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                message.role === "user"
                  ? "ml-auto bg-primary/10 text-foreground"
                  : "mr-auto bg-muted text-foreground",
              )}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              <p className="mt-1 text-[10px] text-muted-foreground">
                {formatDateTime(message.created_at)}
              </p>
            </div>
          ))
        )}
      </div>

      <div className="flex items-end gap-2">
        <Textarea
          placeholder="Ask a question…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          className="min-h-[2.5rem]"
        />
        <Button
          type="button"
          size="icon"
          loading={sendMessage.isPending}
          disabled={!draft.trim()}
          onClick={handleSend}
          aria-label="Send message"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
