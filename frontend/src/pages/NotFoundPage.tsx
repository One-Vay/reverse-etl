import { Compass } from "lucide-react";
import { Link } from "react-router-dom";

import { buttonClasses } from "@/components/ui/Button";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Compass className="h-6 w-6" />
      </div>
      <div>
        <h1 className="text-lg font-semibold">Page not found</h1>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has moved.
        </p>
      </div>
      <Link to="/" className={buttonClasses("primary", "md")}>
        Back to Connections
      </Link>
    </div>
  );
}
