"""Print the --list-tests report."""
from grader.output.formatting import number


def list_tests(info):
    print(f"Core tests: {len(info.core)}")
    for name in info.core:
        print(f"  {name}")
    print(f"Extra-credit tests: {len(info.extra)}")
    for name in info.extra:
        print(f"  {name}")
    print(f"Tiers: {len(info.tiers)}")
    for tier in sorted(info.tiers):
        bonus = info.bonuses.get(tier)
        suffix = f" (+{number(bonus)} bonus if all lower tiers are earned)" if bonus else ""
        print(f"  Tier {tier}: {', '.join(info.tiers[tier])}{suffix}")
    print(f"Warnings: {len(info.warnings)}")
    for warning in info.warnings:
        print(f"  {warning}")
