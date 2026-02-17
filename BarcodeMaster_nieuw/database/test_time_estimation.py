#!/usr/bin/env python3
"""
Test script for project time estimation API endpoint
"""
import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:5001"

def test_basic_estimation():
    """Test basic time estimation with just item count"""
    print("=" * 80)
    print("TEST 1: Basic Time Estimation (100 items)")
    print("=" * 80)

    payload = {
        "items": 100
    }

    response = requests.post(f"{BASE_URL}/api/project/estimate-time", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"\nGlobal Estimate:")
        print(f"  - Estimated Hours: {data['global_estimate']['estimated_hours']}h")
        print(f"  - Best Case: {data['global_estimate']['best_case_hours']}h")
        print(f"  - Worst Case: {data['global_estimate']['worst_case_hours']}h")
        print(f"  - Avg Items/Hour: {data['global_estimate']['avg_items_per_hour']}")
        print(f"  - Confidence: {data['global_estimate']['confidence_level']}")

        print(f"\nHistorical Data:")
        print(f"  - Sample Size: {data['historical_analysis']['sample_size']} sessions")
        print(f"  - Total Items Analyzed: {data['historical_analysis']['total_items_analyzed']}")
        print(f"  - Period: {data['historical_analysis']['data_period']}")

        if data['user_estimates']:
            print(f"\nPer-User Estimates:")
            for user in data['user_estimates'][:5]:  # Show first 5 users
                print(f"  - {user['user']}: {user['estimated_hours']}h @ {user['actual_items_per_hour']} items/hour")

        print()
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)
        return False

def test_optimal_capacity():
    """Test with optimal capacity mode enabled"""
    print("=" * 80)
    print("TEST 2: Optimal Capacity Estimation (150 items)")
    print("=" * 80)

    payload = {
        "items": 150,
        "use_optimal_capacity": True
    }

    response = requests.post(f"{BASE_URL}/api/project/estimate-time", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"\nGlobal Estimate (Optimal Capacity):")
        print(f"  - Estimated Hours: {data['global_estimate']['estimated_hours']}h")

        print(f"\nCapacity Analysis:")
        print(f"  - Using Optimal: {data['capacity_analysis']['using_optimal']}")
        print(f"  - Avg Capacity Utilization: {data['capacity_analysis']['avg_capacity_utilization']}%")

        if data['user_estimates']:
            print(f"\nTop 3 Users (Optimal vs Actual):")
            for user in data['user_estimates'][:3]:
                print(f"  - {user['user']}:")
                print(f"      Actual: {user['actual_items_per_hour']} items/h")
                print(f"      Optimal: {user['optimal_items_per_hour']} items/h")
                print(f"      Estimated: {user['estimated_hours']}h")
                print(f"      Utilization: {user['capacity_utilization_percentage']}%")

        print()
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)
        return False

def test_specific_users():
    """Test with specific assigned users"""
    print("=" * 80)
    print("TEST 3: Specific Users Estimation (200 items for NESTING & OPUS)")
    print("=" * 80)

    payload = {
        "items": 200,
        "assigned_users": ["NESTING", "OPUS"],
        "project_type": "NESTING_PROCESSING"
    }

    response = requests.post(f"{BASE_URL}/api/project/estimate-time", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"\nGlobal Estimate:")
        print(f"  - Estimated Hours: {data['global_estimate']['estimated_hours']}h")

        print(f"\nParallel Processing:")
        if data['parallel_processing']['enabled']:
            print(f"  - Enabled: Yes")
            print(f"  - Users: {data['parallel_processing']['users_count']}")
            print(f"  - Parallel Estimate: {data['parallel_processing']['estimated_hours']}h")
            print(f"  - Time Saved: {data['global_estimate']['estimated_hours'] - data['parallel_processing']['estimated_hours']:.2f}h")

        print(f"\nUser Estimates:")
        for user in data['user_estimates']:
            print(f"  - {user['user']}: {user['estimated_hours']}h ({user['sessions_analyzed']} sessions analyzed)")

        print()
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)
        return False

def test_similar_projects():
    """Test with project reference to find similar historical projects"""
    print("=" * 80)
    print("TEST 4: Similar Projects Analysis (with project reference)")
    print("=" * 80)

    payload = {
        "items": 120,
        "project": "P240912-002"  # Example project
    }

    response = requests.post(f"{BASE_URL}/api/project/estimate-time", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"\nGlobal Estimate:")
        print(f"  - Estimated Hours: {data['global_estimate']['estimated_hours']}h")

        similar = data['historical_analysis']['similar_projects']
        if similar:
            print(f"\nSimilar Historical Projects:")
            for proj in similar:
                print(f"  - {proj['project']}:")
                print(f"      Items: {proj['items']}")
                print(f"      Duration: {proj['duration_hours']}h")
                print(f"      Performance: {proj['items_per_hour']} items/h")
                print(f"      Status: {proj['status']}")
        else:
            print(f"\n⚠️  No similar projects found")

        print()
        return True
    else:
        print(f"❌ Failed: {response.status_code}")
        print(response.text)
        return False

def test_edge_cases():
    """Test edge cases"""
    print("=" * 80)
    print("TEST 5: Edge Cases")
    print("=" * 80)

    # Test with invalid data
    test_cases = [
        ({"items": 0}, "Zero items"),
        ({"items": -10}, "Negative items"),
        ({}, "Missing items"),
    ]

    for payload, description in test_cases:
        response = requests.post(f"{BASE_URL}/api/project/estimate-time", json=payload)
        if response.status_code == 400:
            print(f"✅ {description}: Correctly rejected")
        else:
            print(f"❌ {description}: Should have been rejected (got {response.status_code})")

    print()

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PROJECT TIME ESTIMATION API TESTS")
    print("=" * 80 + "\n")

    try:
        # Run all tests
        test_basic_estimation()
        test_optimal_capacity()
        test_specific_users()
        test_similar_projects()
        test_edge_cases()

        print("=" * 80)
        print("ALL TESTS COMPLETED")
        print("=" * 80 + "\n")

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to API server at " + BASE_URL)
        print("   Make sure the db_log_api.py server is running!")
        print("   Run: python db_log_api.py")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
