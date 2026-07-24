/** 로그인 배경: 은은하게 떠다니는 소프트 블롭(틸/스카이/코랄). CSS 애니메이션. */
export function AnimatedBg() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div
        className="blob"
        style={{ width: 420, height: 420, left: '-6%', top: '-8%', background: 'var(--primary)' }}
      />
      <div
        className="blob"
        style={{ width: 380, height: 380, right: '-4%', top: '6%', background: 'var(--brand2)', animationDelay: '-6s' }}
      />
      <div
        className="blob"
        style={{ width: 360, height: 360, left: '30%', bottom: '-12%', background: 'var(--accent)', animationDelay: '-11s' }}
      />
    </div>
  )
}
