import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => Promise<unknown> | void;
  title: string;
  description?: string;
  confirmLabel?: string;
  destructive?: boolean;
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = "Confirm",
  destructive = true,
}: ConfirmDialogProps) {
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
      onClose();
    } catch {
      // Already surfaced to the user via the mutation's onError toast;
      // keep the dialog open so they can retry or cancel.
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      size="sm"
    >
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          variant={destructive ? "destructive" : "primary"}
          onClick={handleConfirm}
          loading={loading}
        >
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
