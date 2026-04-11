"use client";

import { useState } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
import { Plus, Trash2 } from "lucide-react";
import type { TeamMember, MemberRole } from "@/lib/mock-data/oncall";

interface MemberManagerProps {
  members: TeamMember[];
  onChange: (members: TeamMember[]) => void;
}

const ROLES: MemberRole[] = ["SRE", "Backend", "Platform", "DevOps", "Security"];

const roleBadgeColor: Record<MemberRole, string> = {
  SRE: "text-[#00FF88] bg-[#00FF88]/10 border-[#00FF88]/30",
  Backend: "text-cyan-400 bg-cyan-400/10 border-cyan-400/30",
  Platform: "text-purple-400 bg-purple-400/10 border-purple-400/30",
  DevOps: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  Security: "text-red-400 bg-red-400/10 border-red-400/30",
};

let nextMemberId = 100;

export function MemberManager({ members, onChange }: MemberManagerProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState<MemberRole>("SRE");

  function addMember() {
    if (!newName.trim() || !newEmail.trim()) return;
    const initials = newName
      .trim()
      .split(" ")
      .map((w) => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);

    onChange([
      ...members,
      {
        id: `tm-${++nextMemberId}`,
        name: newName.trim(),
        email: newEmail.trim(),
        role: newRole,
        avatarInitials: initials,
        expertise: [],
      },
    ]);
    setNewName("");
    setNewEmail("");
    setNewRole("SRE");
    setShowAddForm(false);
  }

  function removeMember(id: string) {
    onChange(members.filter((m) => m.id !== id));
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="font-mono text-sm text-muted-foreground">
          {members.length} team members
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          <Plus data-icon="inline-start" />
          Add Member
        </Button>
      </div>

      {/* Add form */}
      {showAddForm && (
        <Card className="border-[#00FF88]/20 bg-card p-4">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="font-mono text-sm text-muted-foreground">
                Name
              </label>
              <Input
                className="mt-1 font-mono text-sm"
                placeholder="Full Name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="flex-1">
              <label className="font-mono text-sm text-muted-foreground">
                Email
              </label>
              <Input
                className="mt-1 font-mono text-sm"
                placeholder="user@aegis.dev"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
              />
            </div>
            <div className="w-36">
              <label className="font-mono text-sm text-muted-foreground">
                Role
              </label>
              <Select
                value={newRole}
                onValueChange={(val) => { if (val) setNewRole(val as MemberRole) }}
              >
                <SelectTrigger className="mt-1 font-mono text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((r) => (
                    <SelectItem key={r} value={r}>
                      {r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              size="sm"
              onClick={addMember}
              disabled={!newName.trim() || !newEmail.trim()}
            >
              Add
            </Button>
          </div>
        </Card>
      )}

      {/* Member grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {members.map((member) => (
          <Card
            key={member.id}
            className={`bg-card p-5 ${member.isOnCall ? "border-[#00FF88]/30" : "border-border/50"}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <Avatar>
                  <AvatarFallback className="font-mono text-xs">
                    {member.avatarInitials}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-mono text-sm font-medium">
                      {member.name}
                    </p>
                    {member.isOnCall && (
                      <Badge
                        variant="outline"
                        className="font-mono text-xs text-[#00FF88] border-[#00FF88]/30 bg-[#00FF88]/10"
                      >
                        ON-CALL
                      </Badge>
                    )}
                  </div>
                  <p className="font-mono text-xs text-muted-foreground">
                    {member.email}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={() => removeMember(member.id)}
              >
                <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
              </Button>
            </div>

            <div className="mt-3">
              <Badge
                variant="outline"
                className={`font-mono text-xs ${roleBadgeColor[member.role]}`}
              >
                {member.role}
              </Badge>
            </div>

            {member.expertise.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {member.expertise.map((tag) => (
                  <span
                    key={tag}
                    className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
