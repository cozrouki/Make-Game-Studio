---
name: unified-agent-controller
description: "Player와 NPC가 동일한 Agent 베이스를 공유하며 IAgentMover 전략으로 입력/NavMesh를 교체하는 통합 에이전트 아키텍처."
version: 1.0.0
tags: ["gameplay", "NPC", "player", "strategy-pattern", "IAgentMover", "state-factory", "DIP"]
argument-hint: "name='PlayerCharacter' namespace='Game.Gameplay.Agent' states='Idle,Move,Jump,Fall'"
disable-model-invocation: false
user-invocable: true
allowed-tools:
  - run_command
  - list_dir
  - write_to_file
requirements:
  unity_version: ">=6.0"
  render_pipeline: "Any"
  dependencies: []
context_discovery:
  check_unity_version: true
  check_render_pipeline: false
  scan_manifest_for: []
performance_budget:
  gc_alloc_per_frame: "0 bytes target in hot paths"
  max_update_cost: "O(1) per agent"
tdd_first: true
---

# Unified Agent Controller

## Overview

Player와 NPC가 **동일한 `Agent` 베이스 클래스**를 공유하는 통합 에이전트 아키텍처.
`IAgentMover` 인터페이스(Strategy Pattern + DIP)로 이동 방식을 런타임에 교체 가능하게 하여, 같은 캐릭터가 플레이어 입력 또는 NavMesh AI로 동작한다.

**출처**: Unity Discussions — "Tips for writing cleaner code that scales in Unity, Part 1"
by Sunny Valley Studio (GitHub: SunnyValleyStudio/Tips-for-writing-cleaner-code-in-Unity)

## 핵심 아이디어: 왜 통합인가?

```
// ❌ 기존 방식: 완전히 다른 두 클래스
class PlayerController : MonoBehaviour { ... } // 입력 처리
class EnemyAI        : MonoBehaviour { ... } // NavMesh 처리

// ✅ 통합 방식: 공유 베이스 + 교체 가능한 전략
class Agent          : MonoBehaviour { IAgentMover _mover; }
class PlayerAgent    : Agent        { _mover = new InputAgentMover(inputReader); }
class NPCAgent       : Agent        { _mover = new NavMeshAgentMover(navAgent); }
```

중복 로직(상태 머신, 애니메이터, 피격 처리)을 `Agent`에 한 번만 작성하고, 이동 방식만 교체한다.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Agent (abstract)                     │
│  - StateMachine<Agent>  _stateMachine                    │
│  - IAgentMover          _mover          ← 핵심 전략       │
│  - Animator, Rigidbody  (공유 컴포넌트)                   │
│  - StateFactory         _stateFactory                    │
└────────────┬──────────────────┬─────────────────────────-┘
             │                  │
    ┌────────┴───────┐  ┌───────┴────────┐
    │  PlayerAgent   │  │   NPCAgent     │
    │ (InputMover)   │  │ (NavMeshMover) │
    └────────────────┘  └────────────────┘

┌─────────────────────────────────────────┐
│           IAgentMover (Strategy)        │
├─────────────────────────────────────────┤
│  void Move(Vector3 direction)           │
│  void RotateTo(Vector3 targetPos)       │
│  bool IsMoving { get; }                 │
└────────────┬────────────────────────────┘
             │
   ┌─────────┴──────────┐
   │                    │
┌──┴────────────┐  ┌────┴─────────────────┐
│InputAgentMover│  │NavMeshAgentMover      │
│(CharController│  │(NavMeshAgent)         │
│ or Rigidbody) │  │                       │
└───────────────┘  └───────────────────────┘

┌─────────────────────────────────────────┐
│           StateFactory                  │
│  CreateIdleState()  : AgentIdleState    │
│  CreateMoveState()  : AgentMoveState    │
│  CreateJumpState()  : AgentJumpState    │
│  CreateFallState()  : AgentFallState    │
└─────────────────────────────────────────┘
```

## Components

| 컴포넌트 | 역할 |
|---------|------|
| `Agent` | 공유 베이스. 상태머신, 애니메이터, 이벤트 보유 |
| `IAgentMover` | 이동 전략 인터페이스 (Strategy + DIP) |
| `InputAgentMover` | 플레이어 입력 → CharacterController 이동 |
| `NavMeshAgentMover` | NavMeshAgent 래퍼 (NPC용) |
| `StateFactory` | 상태 인스턴스 생성 책임 분리 |
| `AgentState` (abstract) | 공통 상태 베이스 (Enter/Exit/Update/FixedUpdate) |
| `PlayerAgent` | 입력 리더 주입, InputAgentMover 생성 |
| `NPCAgent` | NavMesh 목표 주입, NavMeshAgentMover 생성 |

## Procedure

1. **Agent 베이스 정의**: 공유 컴포넌트(Animator, StateMachine, StateFactory) 캐싱
2. **IAgentMover 인터페이스 작성**: Move/RotateTo/IsMoving 계약 정의
3. **Mover 구현**: `InputAgentMover`, `NavMeshAgentMover` 각각 구현
4. **StateFactory 작성**: 각 상태 클래스 생성 책임을 Factory에 위임
5. **AgentState들 작성**: `Agent` 컨텍스트에서 `_mover.Move()` 호출
6. **PlayerAgent / NPCAgent 작성**: `Awake()`에서 적절한 Mover 주입

## Best Practices

- ✅ `Agent`에 `[RequireComponent]`로 Animator, CharacterController 강제
- ✅ `IAgentMover`는 순수 C# 인터페이스 (MonoBehaviour 의존 없음)
- ✅ `StateFactory`를 `Agent`가 소유 — 상태는 팩토리를 통해서만 생성
- ✅ `NPCAgent`는 `NavMeshAgent`를 `GetComponent`로 캐싱 (`Awake()` 에서)
- ✅ 애니메이터 파라미터는 `Animator.StringToHash()` 캐싱
- ❌ **NEVER** `NPCAgent`에서 입력 코드 직접 참조
- ❌ **NEVER** `AgentState`에서 구체 Mover 타입 캐스팅
- ❌ **NEVER** `Agent`에 `if (isNPC)` 분기 추가 — Mover 교체가 해결

## Few-Shot Examples

### Example 1: IAgentMover 인터페이스 + 두 구현체

```csharp
// IAgentMover.cs
public interface IAgentMover
{
    void Move(Vector3 velocity);
    void RotateTo(Vector3 targetPosition);
    bool IsMoving { get; }
}

// InputAgentMover.cs
public class InputAgentMover : IAgentMover
{
    private readonly CharacterController _cc;
    private readonly float _speed;
    private Vector3 _lastVelocity;

    public InputAgentMover(CharacterController cc, float speed)
    {
        _cc = cc;
        _speed = speed;
    }

    public bool IsMoving => _lastVelocity.magnitude > 0.01f;

    public void Move(Vector3 velocity)
    {
        _lastVelocity = velocity;
        _cc.Move(velocity * (_speed * Time.deltaTime));
    }

    public void RotateTo(Vector3 targetPosition)
    {
        var dir = (targetPosition - _cc.transform.position).normalized;
        if (dir.sqrMagnitude < 0.001f) return;
        _cc.transform.rotation = Quaternion.LookRotation(new Vector3(dir.x, 0f, dir.z));
    }
}

// NavMeshAgentMover.cs
public class NavMeshAgentMover : IAgentMover
{
    private readonly NavMeshAgent _navAgent;

    public NavMeshAgentMover(NavMeshAgent navAgent) => _navAgent = navAgent;

    public bool IsMoving => _navAgent.velocity.sqrMagnitude > 0.01f;

    public void Move(Vector3 velocity)
    {
        // NavMesh는 자체 경로 계산 — velocity 직접 제어는 SetDestination으로 대체
        // 외부에서 SetDestination() 호출 후 Move(Vector3.zero)로 idle 표현도 가능
    }

    public void RotateTo(Vector3 targetPosition)
    {
        _navAgent.SetDestination(targetPosition);
    }
}
```

### Example 2: Agent 베이스 클래스

```csharp
// Agent.cs
[RequireComponent(typeof(CharacterController))]
[RequireComponent(typeof(Animator))]
public abstract class Agent : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 5f;

    protected StateMachine<Agent> StateMachine { get; private set; }
    protected StateFactory StateFactory       { get; private set; }
    protected IAgentMover  Mover             { get; private set; }
    protected Animator     AgentAnimator     { get; private set; }

    private static readonly int SpeedHash = Animator.StringToHash("Speed");

    protected virtual void Awake()
    {
        AgentAnimator = GetComponent<Animator>();
        Mover         = CreateMover();     // ← 서브클래스가 전략 결정
        StateFactory  = new StateFactory(this);
        StateMachine  = new StateMachine<Agent>(this);
    }

    protected virtual void Start()
    {
        StateMachine.ChangeState(StateFactory.CreateIdleState());
    }

    protected virtual void Update()    => StateMachine.Update();
    protected virtual void FixedUpdate() => StateMachine.FixedUpdate();

    /// <summary>서브클래스가 적절한 IAgentMover를 반환한다.</summary>
    protected abstract IAgentMover CreateMover();

    public void SetAnimatorSpeed(float speed)
        => AgentAnimator.SetFloat(SpeedHash, speed);
}
```

### Example 3: PlayerAgent vs NPCAgent

```csharp
// PlayerAgent.cs
public class PlayerAgent : Agent
{
    [SerializeField] private InputReader _inputReader;

    protected override IAgentMover CreateMover()
    {
        var cc = GetComponent<CharacterController>();
        return new InputAgentMover(cc, /* speed는 Agent 상위에서 관리 */);
    }

    protected override void Update()
    {
        // 입력 소비 후 상태머신에 전달
        base.Update();
    }
}

// NPCAgent.cs
public class NPCAgent : Agent
{
    private NavMeshAgent _navMeshAgent;

    protected override void Awake()
    {
        _navMeshAgent = GetComponent<NavMeshAgent>();
        base.Awake(); // Awake 순서 주의: NavMeshAgent 먼저 캐싱
    }

    protected override IAgentMover CreateMover()
        => new NavMeshAgentMover(_navMeshAgent);
}
```

### Example 4: StateFactory

```csharp
// StateFactory.cs
public class StateFactory
{
    private readonly Agent _agent;

    public StateFactory(Agent agent) => _agent = agent;

    public AgentState CreateIdleState() => new AgentIdleState(_agent, this);
    public AgentState CreateMoveState() => new AgentMoveState(_agent, this);
    public AgentState CreateJumpState() => new AgentJumpState(_agent, this);
    public AgentState CreateFallState() => new AgentFallState(_agent, this);
}

// AgentState.cs (abstract)
public abstract class AgentState
{
    protected readonly Agent       _agent;
    protected readonly StateFactory _factory;

    protected AgentState(Agent agent, StateFactory factory)
    {
        _agent   = agent;
        _factory = factory;
    }

    public virtual void Enter()        { }
    public virtual void Exit()         { }
    public virtual void Update()       { }
    public virtual void FixedUpdate()  { }
}

// AgentMoveState.cs
public class AgentMoveState : AgentState
{
    public AgentMoveState(Agent agent, StateFactory factory) : base(agent, factory) { }

    public override void FixedUpdate()
    {
        // Mover에 위임 — Player인지 NPC인지 모른다
        _agent.Mover.Move(_agent.MoveDirection);
        _agent.SetAnimatorSpeed(_agent.Mover.IsMoving ? 1f : 0f);
    }
}
```

## TDD Contract

```csharp
// Test 1: InputAgentMover는 Move() 호출 시 CharacterController를 이동시킨다
[Test]
public void InputAgentMover_ShouldMoveCharacter_WhenMoveIsCalled()
{
    // Arrange
    var go     = new GameObject();
    var cc     = go.AddComponent<CharacterController>();
    var mover  = new InputAgentMover(cc, 5f);
    var before = go.transform.position;

    // Act
    mover.Move(Vector3.forward);

    // Assert
    Assert.AreNotEqual(before, go.transform.position);

    Object.DestroyImmediate(go);
}

// Test 2: NavMeshAgentMover.IsMoving은 NavMeshAgent 속도에 따라 반환된다
[Test]
public void NavMeshAgentMover_IsMoving_ShouldReflectNavMeshVelocity()
{
    // NavMeshAgent는 PlayMode에서만 동작하므로 편집 모드 테스트는 Mock 사용
    var mockNav = Substitute.For<INavMeshAgentAdapter>(); // NSubstitute 활용
    mockNav.velocity.Returns(Vector3.forward * 2f);
    var mover = new NavMeshAgentMover(mockNav);

    Assert.IsTrue(mover.IsMoving);
}

// Test 3: StateFactory는 각 상태 타입을 정확히 생성한다
[Test]
public void StateFactory_ShouldCreateCorrectStateType_ForEachCreateMethod()
{
    var agentMock  = Substitute.For<Agent>();
    var factory    = new StateFactory(agentMock);

    Assert.IsInstanceOf<AgentIdleState>(factory.CreateIdleState());
    Assert.IsInstanceOf<AgentMoveState>(factory.CreateMoveState());
}
```

## Related Skills

- `@state-machine-architect` — 범용 FSM 구현 (이 스킬의 StateMachine 기반)
- `@navmesh-pathfinding` — NavMeshAgent 상세 설정
- `@advanced-character-controller` — 플레이어 전용 고급 이동
- `@interface-driven-development` — IAgentMover 같은 계약 기반 설계
- `@ai-behavior-trees` — 더 복잡한 NPC 의사결정이 필요할 때

## Template Files

- `templates/IAgentMover.cs.txt` — 이동 전략 인터페이스
- `templates/Agent.cs.txt` — 추상 에이전트 베이스
- `templates/StateFactory.cs.txt` — 상태 팩토리
- `templates/AgentState.cs.txt` — 추상 상태 베이스
- `templates/InputAgentMover.cs.txt` — 입력 기반 이동 구현체
- `templates/NavMeshAgentMover.cs.txt` — NavMesh 기반 이동 구현체
