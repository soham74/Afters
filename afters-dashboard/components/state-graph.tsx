"use client";

const ORDER: Record<string, number> = {
  awaiting_first_response: 0,
  awaiting_second_response: 1,
  mutual_reveal_ready: 2,
  resolving: 3,
  resolved: 4,
  closed: 4,
};

const NODES = [
  { key: "awaiting_first_response", label: "Awaiting first" },
  { key: "awaiting_second_response", label: "Awaiting second" },
  { key: "mutual_reveal_ready", label: "Mutual reveal" },
  { key: "resolving", label: "Resolving" },
  { key: "resolved", label: "Resolved" },
];

export function StateGraph({
  state,
  outcome,
}: {
  state: string;
  outcome: string | null | undefined;
}) {
  const currentIdx = ORDER[state] ?? 0;
  const isClosed = state === "closed";
  const lastLabel = isClosed ? "Closed" : "Resolved";

  // SVG dimensions chosen so the graph reads from ~10 feet on a shrunken video.
  const width = 1200;
  const nodeHeight = 56;
  const nodeWidth = 200;
  const padX = 24;
  const gap = (width - padX * 2 - nodeWidth * NODES.length) / (NODES.length - 1);
  const yCenter = 46;
  const y = yCenter - nodeHeight / 2;

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${width} ${nodeHeight + 36}`}
        className="w-full h-auto"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <marker
            id="arrow"
            markerWidth="9"
            markerHeight="9"
            refX="7"
            refY="4.5"
            orient="auto"
          >
            <path d="M0,0 L9,4.5 L0,9 z" fill="#A3A3A3" />
          </marker>
        </defs>
        {NODES.map((n, i) => {
          const x = padX + i * (nodeWidth + gap);
          const isPast = i < currentIdx;
          const isCurrent = i === currentIdx;
          const fill = isCurrent ? "#FFE5E1" : isPast ? "#F4F4F5" : "#FFFFFF";
          const stroke = isCurrent ? "#FF6B5E" : isPast ? "#E5E5E5" : "#E5E5E5";
          const textColor = isCurrent
            ? "#E54A3D"
            : isPast
              ? "#737373"
              : "#A3A3A3";
          const weight = isCurrent ? 700 : 500;
          const label =
            i === NODES.length - 1 && (isClosed || currentIdx === 4)
              ? lastLabel
              : n.label;
          return (
            <g key={n.key}>
              <rect
                x={x}
                y={y}
                width={nodeWidth}
                height={nodeHeight}
                rx={14}
                fill={fill}
                stroke={stroke}
                strokeWidth={isCurrent ? 2.5 : 1.5}
              />
              {isPast && (
                <circle
                  cx={x + 22}
                  cy={yCenter}
                  r={7}
                  fill="#10B981"
                  stroke="#FAFAFA"
                  strokeWidth={1.5}
                />
              )}
              {isPast && (
                <path
                  d={`M${x + 18.5} ${yCenter} L${x + 21.5} ${yCenter + 3} L${x + 25.5} ${yCenter - 3}`}
                  stroke="#fff"
                  strokeWidth={1.8}
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}
              {isCurrent && (
                <circle
                  cx={x + 22}
                  cy={yCenter}
                  r={6}
                  fill="#FF6B5E"
                />
              )}
              <text
                x={x + nodeWidth / 2 + (isPast || isCurrent ? 10 : 0)}
                y={yCenter + 5}
                textAnchor="middle"
                fontSize={15}
                fontWeight={weight}
                fill={textColor}
                fontFamily="Inter, system-ui, sans-serif"
              >
                {label}
              </text>
              {i < NODES.length - 1 && (
                <line
                  x1={x + nodeWidth + 2}
                  y1={yCenter}
                  x2={x + nodeWidth + gap - 6}
                  y2={yCenter}
                  stroke={i < currentIdx ? "#737373" : "#D4D4D4"}
                  strokeWidth={1.8}
                  markerEnd="url(#arrow)"
                />
              )}
            </g>
          );
        })}
        {outcome && (
          <text
            x={width / 2}
            y={nodeHeight + 28}
            textAnchor="middle"
            fontSize={13}
            fontWeight={500}
            fill="#737373"
            fontFamily="Inter, system-ui, sans-serif"
          >
            outcome: {outcome}
          </text>
        )}
      </svg>
    </div>
  );
}
