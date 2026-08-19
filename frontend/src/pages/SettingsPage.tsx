import { zodResolver } from "@hookform/resolvers/zod";
import { Download, Send, Sparkles, Timer, MessageCircle } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { Switch } from "@/components/ui/Switch";
import {
  useLLMStatus,
  usePullLLMModel,
  useSendTelegramTestMessage,
  useSettings,
  useUpdateSettings,
} from "@/hooks/useSettings";
import { type SettingsFormValues, settingsSchema } from "@/lib/schemas";

export function SettingsPage() {
  const settingsQuery = useSettings();
  const updateSettings = useUpdateSettings();

  const {
    register,
    watch,
    setValue,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      scheduler_enabled: true,
      scheduler_poll_interval_seconds: 30,
      llm_enabled: false,
      llm_base_url: "http://ollama:11434",
      llm_model: "qwen2.5:0.5b",
      telegram_enabled: false,
      telegram_bot_token: "",
      telegram_chat_id: "",
      default_connect_timeout_seconds: 10,
      default_request_timeout_seconds: 30,
    },
  });

  useEffect(() => {
    if (settingsQuery.data) reset(settingsQuery.data);
  }, [settingsQuery.data, reset]);

  const schedulerEnabled = watch("scheduler_enabled");
  const llmEnabled = watch("llm_enabled");
  const telegramEnabled = watch("telegram_enabled");

  const llmStatusQuery = useLLMStatus(llmEnabled);
  const pullModel = usePullLLMModel();
  const sendTelegramTest = useSendTelegramTestMessage();

  const onSubmit = async (values: SettingsFormValues) => {
    try {
      await updateSettings.mutateAsync(values);
    } catch {
      // Already surfaced to the user via the mutation's onError toast.
    }
  };

  if (settingsQuery.isLoading) {
    return (
      <AppShell title="Settings" description="Scheduler and AI mapping suggestions.">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Settings"
      description="Every operational setting below is applied immediately — no redeploy needed."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-1.5">
                <Timer className="h-4 w-4" /> Scheduler
              </CardTitle>
              <CardDescription>
                Controls the background loop that runs due pipelines automatically.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <label htmlFor="scheduler-enabled" className="text-sm font-medium">
                  Enabled
                </label>
                <Switch
                  checked={schedulerEnabled}
                  onCheckedChange={(checked) =>
                    setValue("scheduler_enabled", checked, { shouldDirty: true })
                  }
                  label="Scheduler enabled"
                />
              </div>
              <FormField
                label="Poll interval (seconds)"
                htmlFor="scheduler-poll-interval"
                error={errors.scheduler_poll_interval_seconds?.message}
                hint="How often to check for due pipelines. 5–3600 seconds."
              >
                <Input
                  id="scheduler-poll-interval"
                  type="number"
                  disabled={!schedulerEnabled}
                  {...register("scheduler_poll_interval_seconds")}
                />
              </FormField>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  label="Default connect timeout (s)"
                  htmlFor="default-connect-timeout"
                  error={errors.default_connect_timeout_seconds?.message}
                  hint="Used by new connections unless overridden."
                >
                  <Input
                    id="default-connect-timeout"
                    type="number"
                    step="0.5"
                    {...register("default_connect_timeout_seconds")}
                  />
                </FormField>
                <FormField
                  label="Default request timeout (s)"
                  htmlFor="default-request-timeout"
                  error={errors.default_request_timeout_seconds?.message}
                >
                  <Input
                    id="default-request-timeout"
                    type="number"
                    step="0.5"
                    {...register("default_request_timeout_seconds")}
                  />
                </FormField>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-1.5">
                <Sparkles className="h-4 w-4" /> AI mapping suggestions
              </CardTitle>
              <CardDescription>
                Optional local LLM (via Ollama) that suggests field mappings in the
                pipeline editor. Nothing is sent anywhere outside your own network.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <label htmlFor="llm-enabled" className="text-sm font-medium">
                  Enabled
                </label>
                <Switch
                  checked={llmEnabled}
                  onCheckedChange={(checked) =>
                    setValue("llm_enabled", checked, { shouldDirty: true })
                  }
                  label="AI mapping suggestions enabled"
                />
              </div>
              <FormField
                label="Ollama base URL"
                htmlFor="llm-base-url"
                error={errors.llm_base_url?.message}
                hint="http://ollama:11434 if running via docker compose --profile llm up"
              >
                <Input
                  id="llm-base-url"
                  disabled={!llmEnabled}
                  {...register("llm_base_url")}
                />
              </FormField>
              <FormField
                label="Model"
                htmlFor="llm-model"
                error={errors.llm_model?.message}
                hint="Pulled automatically the first time it's needed."
              >
                <Input id="llm-model" disabled={!llmEnabled} {...register("llm_model")} />
              </FormField>

              {llmEnabled && (
                <div className="flex items-center justify-between rounded-md border border-border bg-muted/30 px-3 py-2 text-xs">
                  <LLMStatusText
                    isLoading={llmStatusQuery.isLoading}
                    isError={llmStatusQuery.isError}
                    modelPresent={llmStatusQuery.data?.model_present}
                    pulling={llmStatusQuery.data?.pulling}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    loading={pullModel.isPending}
                    disabled={llmStatusQuery.data?.pulling}
                    onClick={() => pullModel.mutate()}
                  >
                    <Download className="h-3.5 w-3.5" /> Pull model
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-1.5">
                <MessageCircle className="h-4 w-4" /> Telegram notifications
              </CardTitle>
              <CardDescription>
                Get a report in Telegram every time a scheduled pipeline run finishes —
                including a warning when a run started late (e.g. after the container was
                restarted).
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <label htmlFor="telegram-enabled" className="text-sm font-medium">
                  Enabled
                </label>
                <Switch
                  checked={telegramEnabled}
                  onCheckedChange={(checked) =>
                    setValue("telegram_enabled", checked, { shouldDirty: true })
                  }
                  label="Telegram notifications enabled"
                />
              </div>
              <FormField
                label="Bot token"
                htmlFor="telegram-bot-token"
                error={errors.telegram_bot_token?.message}
                hint="From @BotFather, e.g. 123456:AAExample"
              >
                <Input
                  id="telegram-bot-token"
                  type="password"
                  disabled={!telegramEnabled}
                  {...register("telegram_bot_token")}
                />
              </FormField>
              <FormField
                label="Chat ID"
                htmlFor="telegram-chat-id"
                error={errors.telegram_chat_id?.message}
                hint="Your own personal chat ID (not the bot's ID from BotFather) — e.g. message @userinfobot to get it. Message your bot at least once (e.g. /start) before testing, too — Telegram only lets a bot message chats it has already seen."
              >
                <Input
                  id="telegram-chat-id"
                  disabled={!telegramEnabled}
                  {...register("telegram_chat_id")}
                />
              </FormField>

              {telegramEnabled && (
                <div className="flex items-center justify-between rounded-md border border-border bg-muted/30 px-3 py-2 text-xs">
                  <span className="text-muted-foreground">
                    Uses the last saved token/chat ID — save first if you just changed
                    them.
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    loading={sendTelegramTest.isPending}
                    onClick={() => sendTelegramTest.mutate()}
                  >
                    <Send className="h-3.5 w-3.5" /> Send test message
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-end">
          <Button type="submit" loading={updateSettings.isPending} disabled={!isDirty}>
            Save settings
          </Button>
        </div>
      </form>
    </AppShell>
  );
}

function LLMStatusText({
  isLoading,
  isError,
  modelPresent,
  pulling,
}: {
  isLoading: boolean;
  isError: boolean;
  modelPresent: boolean | undefined;
  pulling: boolean | undefined;
}) {
  if (isLoading) return <span className="text-muted-foreground">Checking model status…</span>;
  if (isError)
    return <span className="text-destructive">Couldn't reach Ollama.</span>;
  if (pulling) return <span className="text-primary">Downloading model…</span>;
  if (modelPresent) return <span className="text-success">Model ready.</span>;
  return <span className="text-muted-foreground">Model not downloaded yet.</span>;
}
