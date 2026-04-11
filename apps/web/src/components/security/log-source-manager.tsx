"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Wifi,
  WifiOff,
  AlertCircle,
  Plus,
  Trash2,
  RefreshCw,
} from "lucide-react";
import type { LogSource, LogSourceType } from "@/lib/mock-data/security";

interface LogSourceManagerProps {
  sources: LogSource[];
  onChange: (sources: LogSource[]) => void;
}

const SOURCE_TYPES: LogSourceType[] = [
  "SigNoz",
  "Datadog",
  "Splunk",
  "CloudWatch",
  "Custom",
];

const statusConfig: Record<
  string,
  { icon: typeof Wifi; color: string; label: string }
> = {
  connected: {
    icon: Wifi,
    color: "text-[#00FF88]",
    label: "Connected",
  },
  disconnected: {
    icon: WifiOff,
    color: "text-muted-foreground",
    label: "Disconnected",
  },
  error: {
    icon: AlertCircle,
    color: "text-red-400",
    label: "Error",
  },
};

let nextSourceId = 100;

export function LogSourceManager({
  sources,
  onChange,
}: LogSourceManagerProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState<LogSourceType>("SigNoz");
  const [newEndpoint, setNewEndpoint] = useState("");
  const [newApiKey, setNewApiKey] = useState("");
  const [testingId, setTestingId] = useState<string | null>(null);

  function addSource() {
    if (!newName.trim() || !newEndpoint.trim()) return;
    onChange([
      ...sources,
      {
        id: `ls-${++nextSourceId}`,
        name: newName.trim(),
        type: newType,
        endpoint: newEndpoint.trim(),
        status: "disconnected",
      },
    ]);
    setNewName("");
    setNewEndpoint("");
    setNewApiKey("");
    setShowAddForm(false);
  }

  function removeSource(id: string) {
    onChange(sources.filter((s) => s.id !== id));
  }

  function testConnection(id: string) {
    setTestingId(id);
    // Simulate connection test
    setTimeout(() => {
      onChange(
        sources.map((s) =>
          s.id === id
            ? {
                ...s,
                status: "connected" as const,
                lastSeen: new Date().toISOString(),
              }
            : s
        )
      );
      setTestingId(null);
    }, 1500);
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="font-mono text-sm text-muted-foreground">
          {sources.filter((s) => s.status === "connected").length} of{" "}
          {sources.length} sources connected
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          <Plus data-icon="inline-start" />
          Add Source
        </Button>
      </div>

      {/* Add form */}
      {showAddForm && (
        <Card className="border-[#00FF88]/20 bg-card p-4">
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-mono text-sm text-muted-foreground">
                  Name
                </label>
                <Input
                  className="mt-1 font-mono text-sm"
                  placeholder="e.g. Splunk Cloud"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
              </div>
              <div>
                <label className="font-mono text-sm text-muted-foreground">
                  Type
                </label>
                <Select
                  value={newType}
                  onValueChange={(val) => { if (val) setNewType(val as LogSourceType) }}
                >
                  <SelectTrigger className="mt-1 font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SOURCE_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <label className="font-mono text-sm text-muted-foreground">
                Endpoint URL
              </label>
              <Input
                className="mt-1 font-mono text-sm"
                placeholder="https://..."
                value={newEndpoint}
                onChange={(e) => setNewEndpoint(e.target.value)}
              />
            </div>
            <div>
              <label className="font-mono text-sm text-muted-foreground">
                API Key
              </label>
              <Input
                type="password"
                className="mt-1 font-mono text-sm"
                placeholder="sk-..."
                value={newApiKey}
                onChange={(e) => setNewApiKey(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowAddForm(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={addSource}
                disabled={!newName.trim() || !newEndpoint.trim()}
              >
                Add Source
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Source cards */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {sources.map((source) => {
          const cfg = statusConfig[source.status];
          const StatusIcon = cfg.icon;
          const isTesting = testingId === source.id;

          return (
            <Card
              key={source.id}
              className={`border-border/50 bg-card p-5 ${source.status === "connected" ? "border-[#00FF88]/20" : ""}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <StatusIcon className={`h-5 w-5 ${cfg.color}`} />
                  <div>
                    <p className="font-mono text-sm font-medium">
                      {source.name}
                    </p>
                    <Badge
                      variant="outline"
                      className="mt-1 font-mono text-xs"
                    >
                      {source.type}
                    </Badge>
                  </div>
                </div>
                <span className={`font-mono text-xs ${cfg.color}`}>
                  {cfg.label}
                </span>
              </div>

              <p className="mt-3 truncate font-mono text-sm text-muted-foreground">
                {source.endpoint}
              </p>

              {source.lastSeen && (
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  Last seen:{" "}
                  {new Date(source.lastSeen).toLocaleString()}
                </p>
              )}

              <div className="mt-4 flex items-center gap-2">
                <Button
                  variant="outline"
                  size="xs"
                  onClick={() => testConnection(source.id)}
                  disabled={isTesting}
                >
                  <RefreshCw
                    data-icon="inline-start"
                    className={isTesting ? "animate-spin" : ""}
                  />
                  {isTesting ? "Testing..." : "Test"}
                </Button>
                <Button
                  variant="ghost"
                  size="xs"
                  onClick={() => removeSource(source.id)}
                >
                  <Trash2 data-icon="inline-start" />
                  Remove
                </Button>
              </div>
            </Card>
          );
        })}

        {sources.length === 0 && (
          <div className="col-span-full rounded border border-dashed border-border/50 p-8 text-center">
            <WifiOff className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-2 font-mono text-sm text-muted-foreground">
              No log sources configured. Add one to start receiving security
              events.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
