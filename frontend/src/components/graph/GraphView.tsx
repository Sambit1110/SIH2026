"use client";

import { useMemo, useCallback } from "react";
import ReactFlow, {
  Background, Controls, MiniMap, type Node, type Edge,
  MarkerType, useNodesState, useEdgesState,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphData } from "@/lib/api";

const NODE_COLORS: Record<string, string> = {
  email: "var(--accent)",
  sender: "var(--info)",
  reply_to: "var(--high)",
  domain: "var(--medium)",
  ip: "var(--medium)",
  asn: "var(--text-muted)",
  url: "var(--high)",
  mx: "var(--text-muted)",
  campaign: "var(--accent)",
};

// Stable, module-level empty objects -- we use React Flow's default node/edge
// rendering only. Passing a fresh {} literal as a prop on every render
// triggers React Flow's "new nodeTypes/edgeTypes object" perf warning even
// when the type map itself is empty, since it re-derives internal state each
// time the reference changes.
const NODE_TYPES = {};
const EDGE_TYPES = {};

const RISK_BORDER: Record<string, string> = {
  HIGH: "var(--critical)",
  MEDIUM: "var(--high)",
  LOW: "var(--border-strong)",
  INFO: "var(--accent)",
};

function layoutNodes(graph: GraphData): Node[] {
  const byType: Record<string, number> = {};
  const colX: Record<string, number> = {
    email: 0, sender: 260, reply_to: 260, domain: 520, ip: 520,
    asn: 780, mx: 780, url: 780, campaign: 0,
  };
  return graph.nodes.map((n) => {
    const x = colX[n.type] ?? 1000;
    const y = (byType[n.type] ?? 0) * 90;
    byType[n.type] = (byType[n.type] ?? 0) + 1;
    return {
      id: n.id,
      position: { x, y },
      data: { label: n.label, type: n.type, raw: n.data },
      style: {
        background: "var(--surface)",
        border: `1.5px solid ${RISK_BORDER[n.risk] ?? "var(--border-strong)"}`,
        borderRadius: 8,
        padding: "8px 12px",
        color: "var(--text)",
        fontSize: 11,
        width: 210,
      },
    };
  });
}

function layoutEdges(graph: GraphData): Edge[] {
  return graph.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.relation.replace(/_/g, " "),
    labelStyle: { fill: "var(--text-faint)", fontSize: 9 },
    style: { stroke: "var(--border-strong)" },
    markerEnd: { type: MarkerType.ArrowClosed, color: "var(--border-strong)", width: 14, height: 14 },
  }));
}

export function GraphView({ graph, onSelectNode }: { graph: GraphData; onSelectNode?: (nodeId: string, data: Record<string, unknown>) => void }) {
  const initialNodes = useMemo(() => layoutNodes(graph), [graph]);
  const initialEdges = useMemo(() => layoutEdges(graph), [graph]);
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onSelectNode?.(node.id, (node.data?.raw as Record<string, unknown>) ?? {});
    },
    [onSelectNode],
  );

  if (graph.nodes.length === 0) {
    return <div className="flex items-center justify-center h-full text-sm text-[var(--text-muted)]">No relationships to display.</div>;
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      edgeTypes={EDGE_TYPES}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={handleNodeClick}
      fitView
      proOptions={{ hideAttribution: true }}
    >
      <Background color="var(--border)" gap={20} />
      <Controls showInteractive={false} />
      <MiniMap
        pannable zoomable
        nodeColor={(n) => NODE_COLORS[(n.data?.type as string) ?? ""] ?? "var(--border-strong)"}
        maskColor="rgba(7,10,16,0.75)"
        style={{ background: "var(--surface)" }}
      />
    </ReactFlow>
  );
}
