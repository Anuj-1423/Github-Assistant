"use client";

import React, { useEffect, useState, useMemo } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap,
  Node,
  Edge,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';

interface GraphViewProps {
  repoId: string;
  apiBase: string;
}

export default function GraphView({ repoId, apiBase }: GraphViewProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchGraph() {
      try {
        const res = await fetch(`${apiBase}/api/repos/${repoId}/graph`);
        const data = await res.json();
        
        // Convert NetworkX format to ReactFlow format
        const rfNodes: Node[] = data.nodes.map((n: any, idx: number) => ({
          id: n.id,
          data: { label: n.name || n.id.split('/').pop() },
          position: { x: Math.random() * 800, y: Math.random() * 600 },
          type: n.type === 'file' ? 'input' : n.type === 'function' ? 'default' : 'output',
          style: {
            background: n.type === 'file' ? '#1E1E2E' : n.type === 'function' ? '#313244' : '#45475a',
            color: '#cdd6f4',
            border: '1px solid #cba6f7',
            borderRadius: '8px',
            fontSize: '10px',
            width: 150,
          },
        }));

        const rfEdges: Edge[] = data.links.map((l: any, idx: number) => ({
          id: `e-${idx}`,
          source: l.source,
          target: l.target,
          label: l.relation,
          animated: l.relation === 'calls',
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#cba6f7',
          },
          style: { stroke: '#cba6f7' },
        }));

        setNodes(rfNodes);
        setEdges(rfEdges);
      } catch (e) {
        console.error("Failed to fetch graph", e);
      } finally {
        setLoading(false);
      }
    }

    if (repoId) {
      fetchGraph();
    }
  }, [repoId, apiBase]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-canvas text-text-muted">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary-brand border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs font-bold uppercase tracking-widest">Loading Relationship Graph...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 h-full w-full bg-canvas relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        onNodesChange={() => {}}
        onEdgesChange={() => {}}
      >
        <Background color="#1e1e2e" gap={20} />
        <Controls />
        <MiniMap 
          nodeColor={(n) => {
            if (n.type === 'input') return '#1E1E2E';
            if (n.type === 'default') return '#313244';
            return '#45475a';
          }}
          maskColor="rgba(30, 30, 46, 0.7)"
        />
      </ReactFlow>
      
      {/* Legend */}
      <div className="absolute top-4 right-4 bg-surface/80 backdrop-blur-md p-4 rounded-panel border border-border-subtle z-10 space-y-3 shadow-2xl">
        <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-widest border-b border-border-subtle pb-2">Legend</h4>
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-[#1E1E2E] border border-[#cba6f7] rounded-sm"></div>
          <span className="text-[10px] font-bold">File</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-[#313244] border border-[#cba6f7] rounded-sm"></div>
          <span className="text-[10px] font-bold">Function</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-[#45475a] border border-[#cba6f7] rounded-sm"></div>
          <span className="text-[10px] font-bold">Class</span>
        </div>
      </div>
    </div>
  );
}
