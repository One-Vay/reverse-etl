import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, PlugZap, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import type { ConnectionTestResult, Source } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import {
  useCreateSource,
  useTestSourceConnection,
  useUpdateSource,
} from "@/hooks/useSources";
import { type SourceFormValues, sourceSchema } from "@/lib/schemas";
import { cn } from "@/lib/utils";

interface SourceFormModalProps {
  open: boolean;
  onClose: () => void;
  source?: Source | null;
}

const DEFAULT_VALUES: SourceFormValues = {
  name: "",
  type: "postgres",
  host: "",
  port: 5432,
  database: "",
  username: "",
  password: "",
};

export function SourceFormModal({ open, onClose, source }: SourceFormModalProps) {
  const isEditing = Boolean(source);
  const createSource = useCreateSource();
  const updateSource = useUpdateSource();
  const testConnection = useTestSourceConnection();
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<SourceFormValues>({
    resolver: zodResolver(sourceSchema),
    defaultValues: DEFAULT_VALUES,
  });

  useEffect(() => {
    if (!open) return;
    setTestResult(null);
    reset(
      source
        ? {
            name: source.name,
            type: source.type,
            host: source.host,
            port: source.port,
            database: source.database,
            username: source.username,
            password: "",
          }
        : DEFAULT_VALUES,
    );
  }, [open, source, reset]);

  const handleTestConnection = async () => {
    if (!source) return;
    setTestResult(null);
    try {
      const result = await testConnection.mutateAsync(source.id);
      setTestResult(result);
    } catch {
      // Already surfaced to the user via the mutation's onError toast.
    }
  };

  const isSaving = createSource.isPending || updateSource.isPending;

  const onSubmit = async (values: SourceFormValues) => {
    const { password, ...rest } = values;
    try {
      if (isEditing && source) {
        await updateSource.mutateAsync({
          id: source.id,
          input: password ? values : rest,
        });
      } else {
        if (!password) {
          setError("password", { message: "Password is required" });
          return;
        }
        await createSource.mutateAsync({ ...values, password });
      }
      onClose();
    } catch {
      // Already surfaced to the user via the mutation's onError toast.
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEditing ? "Edit source" : "Connect a data source"}
      description="PostgreSQL and ClickHouse databases can be used as sync origins."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <FormField
          label="Name"
          htmlFor="source-name"
          error={errors.name?.message}
          required
        >
          <Input
            id="source-name"
            placeholder="Production Postgres"
            {...register("name")}
          />
        </FormField>

        <div className="grid grid-cols-2 gap-4">
          <FormField label="Type" htmlFor="source-type" required>
            <Select id="source-type" {...register("type")}>
              <option value="postgres">PostgreSQL</option>
              <option value="clickhouse">ClickHouse</option>
            </Select>
          </FormField>
          <FormField
            label="Port"
            htmlFor="source-port"
            error={errors.port?.message}
            required
          >
            <Input id="source-port" type="number" {...register("port")} />
          </FormField>
        </div>

        <FormField
          label="Host"
          htmlFor="source-host"
          error={errors.host?.message}
          required
        >
          <Input
            id="source-host"
            placeholder="db.internal.example.com"
            {...register("host")}
          />
        </FormField>

        <FormField
          label="Database"
          htmlFor="source-database"
          error={errors.database?.message}
          required
        >
          <Input id="source-database" placeholder="analytics" {...register("database")} />
        </FormField>

        <div className="grid grid-cols-2 gap-4">
          <FormField
            label="Username"
            htmlFor="source-username"
            error={errors.username?.message}
            required
          >
            <Input id="source-username" {...register("username")} />
          </FormField>
          <FormField
            label="Password"
            htmlFor="source-password"
            error={errors.password?.message}
            hint={isEditing ? "Leave blank to keep the current password" : undefined}
            required={!isEditing}
          >
            <Input
              id="source-password"
              type="password"
              placeholder={isEditing ? "••••••••" : undefined}
              {...register("password")}
            />
          </FormField>
        </div>

        {isEditing && (
          <div className="flex items-center gap-2 rounded-md border border-border bg-muted/40 px-3 py-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleTestConnection}
              loading={testConnection.isPending}
            >
              <PlugZap className="h-3.5 w-3.5" />
              Test connection
            </Button>
            {testResult && (
              <span
                className={cn(
                  "flex items-center gap-1.5 text-xs",
                  testResult.success ? "text-success" : "text-destructive",
                )}
              >
                {testResult.success ? (
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                ) : (
                  <XCircle className="h-3.5 w-3.5 shrink-0" />
                )}
                {testResult.message}
              </span>
            )}
          </div>
        )}

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={isSaving}>
            {isEditing ? "Save changes" : "Connect source"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
