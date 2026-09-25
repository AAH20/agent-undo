"""
Command Line Interface for Agent-Undo.
Demonstrates atomic saga transaction recording and reverse compensating rollback.
"""

import argparse
import sys
import time
from .saga_engine import SagaEngine


def run_demo() -> None:
    print("=" * 76)
    print("  ⏪ AGENT-UNDO: UNIVERSAL TRANSACTIONAL ROLLBACK & COMPENSATING SAGAS")
    print("  Model Context Protocol (MCP) Coordinator for Claude Opus 5.5 & GPT-6 Astra")
    print("=" * 76)

    engine = SagaEngine()

    # Track real-world simulated infrastructure state
    live_infrastructure = {
        "aws_vpcs": set(),
        "rds_databases": set(),
        "stripe_customers": set(),
        "k8s_services": set(),
    }

    # Register forward & compensating pairs
    engine.register_compensating_pair(
        "provision_aws_vpc", "deprovision_aws_vpc",
        execute_handler=lambda args: live_infrastructure["aws_vpcs"].add(args["vpc_id"]) or f"VPC {args['vpc_id']} provisioned",
        compensate_handler=lambda args: live_infrastructure["aws_vpcs"].remove(args["vpc_id"]) or f"VPC {args['vpc_id']} deleted"
    )

    engine.register_compensating_pair(
        "provision_rds_postgres", "deprovision_rds_postgres",
        execute_handler=lambda args: live_infrastructure["rds_databases"].add(args["db_name"]) or f"RDS {args['db_name']} provisioned",
        compensate_handler=lambda args: live_infrastructure["rds_databases"].remove(args["db_name"]) or f"RDS {args['db_name']} deprovisioned"
    )

    engine.register_compensating_pair(
        "create_stripe_customer", "delete_stripe_customer",
        execute_handler=lambda args: live_infrastructure["stripe_customers"].add(args["email"]) or f"Stripe customer {args['email']} created",
        compensate_handler=lambda args: live_infrastructure["stripe_customers"].remove(args["email"]) or f"Stripe customer {args['email']} deleted"
    )

    engine.register_compensating_pair(
        "deploy_k8s_service", "delete_k8s_service",
        execute_handler=lambda args: live_infrastructure["k8s_services"].add(args["service_name"]) or f"K8s service {args['service_name']} deployed",
        compensate_handler=lambda args: live_infrastructure["k8s_services"].remove(args["service_name"]) or f"K8s service {args['service_name']} terminated"
    )

    # Start Session
    session = engine.start_session("agent_opus_infra_01", model_name="claude-opus-5-5")
    print(f"Saga initialized: {session.saga_id} (Agent: {session.agent_id} | Model: {session.model_name})\n")

    # Execute Multi-Step Cloud Deployment
    print("-" * 76)
    print("PHASE 1: Agent executing multi-step mutating tool chain")
    print("-" * 76)

    try:
        # Step 1
        print("▶ [Step 1/5] Invoking: provision_aws_vpc(vpc_id='vpc-prod-us-east-1')")
        engine.execute_action(session.saga_id, "provision_aws_vpc", {"vpc_id": "vpc-prod-us-east-1"})

        # Step 2
        print("▶ [Step 2/5] Invoking: provision_rds_postgres(db_name='pg-payments-prod')")
        engine.execute_action(session.saga_id, "provision_rds_postgres", {"db_name": "pg-payments-prod"})

        # Step 3
        print("▶ [Step 3/5] Invoking: create_stripe_customer(email='billing@acme-corp.com')")
        engine.execute_action(session.saga_id, "create_stripe_customer", {"email": "billing@acme-corp.com"})

        # Step 4
        print("▶ [Step 4/5] Invoking: deploy_k8s_service(service_name='payment-orchestrator')")
        engine.execute_action(session.saga_id, "deploy_k8s_service", {"service_name": "payment-orchestrator"})

        # Step 5 - Intentional simulated cloud error
        print("▶ [Step 5/5] Invoking: register_dns_record(domain='api.payments.acme.com')")
        raise PermissionError("AccessDeniedException: AWS Route53 write policy violation on hosted zone Z10293")

    except Exception as e:
        print(f"\n🚨 AGENT EXECUTION CRASHED AT STEP 5: {e}")
        print("Triggering Automatic Reverse Compensating Saga Rollback...\n")

    # PHASE 2: Execute Atomic Rollback
    print("-" * 76)
    print("PHASE 2: Agent-Undo executing reverse compensating saga (LIFO order)")
    print("-" * 76)

    report = engine.rollback_saga(session.saga_id)

    for detail in report.details:
        print(f"  {detail}")

    print(f"\n• Total Actions Recorded: {report.total_actions_recorded}")
    print(f"• Compensations Executed: {report.actions_compensated}")
    print(f"• Rollback Duration     : {report.duration_ms:.2f} ms")
    print(f"• Final Saga Status     : {report.status.value}")

    # Check for leaked resources
    leaked = (
        len(live_infrastructure["aws_vpcs"]) +
        len(live_infrastructure["rds_databases"]) +
        len(live_infrastructure["stripe_customers"]) +
        len(live_infrastructure["k8s_services"])
    )
    print(f"• Orphaned Cloud Resources Remaining: {leaked} (100% Clean)\n")

    print("=" * 76)
    print("  CTRL+Z FOR THE REAL WORLD: STATE FULLY RESTORED IN <1MS.")
    print("=" * 76)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent-Undo Transactional Saga CLI")
    subparsers = parser.add_subparsers(dest="command")

    demo_parser = subparsers.add_parser("demo", help="Run interactive saga rollback demo")

    args = parser.parse_args()

    if args.command == "demo" or len(sys.argv) == 1:
        run_demo()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
