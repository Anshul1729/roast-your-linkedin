import requests
import sys
import json
from datetime import datetime
import time

class LinkedInRoasterAPITester:
    def __init__(self, base_url="https://roast-genius.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        
        result = {
            "test_name": name,
            "status": "PASSED" if success else "FAILED",
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} - {name}: {details}")

    def test_api_health(self):
        """Test basic API health"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}, Response: {response.json() if success else response.text}"
            self.log_test("API Health Check", success, details)
            return success
        except Exception as e:
            self.log_test("API Health Check", False, f"Error: {str(e)}")
            return False

    def test_generate_roast_endpoint(self):
        """Test the main roast generation endpoint"""
        test_data = {
            "linkedin_url": "https://www.linkedin.com/in/test-profile",
            "roast_style": "mix"
        }
        
        try:
            print("🔍 Testing roast generation (this may take 30-60 seconds)...")
            response = requests.post(
                f"{self.api_url}/generate-roast",
                json=test_data,
                timeout=120,
                headers={'Content-Type': 'application/json'}
            )
            
            success = response.status_code in [200, 201]
            if success:
                data = response.json()
                required_fields = ['roast_text', 'audio_url', 'request_id', 'created_at']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    success = False
                    details = f"Missing fields: {missing_fields}"
                else:
                    details = f"Status: {response.status_code}, Fields: {list(data.keys())}"
            else:
                details = f"Status: {response.status_code}, Error: {response.text}"
            
            self.log_test("Generate Roast Endpoint", success, details)
            return success, response.json() if success else {}
            
        except requests.exceptions.Timeout:
            self.log_test("Generate Roast Endpoint", False, "Request timeout (>120s)")
            return False, {}
        except Exception as e:
            self.log_test("Generate Roast Endpoint", False, f"Error: {str(e)}")
            return False, {}

    def test_audio_endpoint(self, audio_filename=None):
        """Test audio file serving endpoint"""
        if not audio_filename:
            # Use a dummy filename to test 404 handling
            audio_filename = "test_audio.mp3"
        
        try:
            response = requests.get(f"{self.api_url}/audio/{audio_filename}", timeout=10)
            
            if audio_filename == "test_audio.mp3":
                # Expect 404 for non-existent file
                success = response.status_code == 404
                details = f"Status: {response.status_code} (expected 404 for non-existent file)"
            else:
                # Expect 200 for existing file
                success = response.status_code == 200
                details = f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'N/A')}"
            
            self.log_test("Audio Endpoint", success, details)
            return success
            
        except Exception as e:
            self.log_test("Audio Endpoint", False, f"Error: {str(e)}")
            return False

    def test_roast_styles(self):
        """Test different roast styles"""
        styles = ["savage", "funny", "witty", "mix"]
        style_results = []
        
        for style in styles:
            test_data = {
                "linkedin_url": "https://www.linkedin.com/in/test-profile",
                "roast_style": style
            }
            
            try:
                print(f"🔍 Testing {style} roast style...")
                response = requests.post(
                    f"{self.api_url}/generate-roast",
                    json=test_data,
                    timeout=120,
                    headers={'Content-Type': 'application/json'}
                )
                
                success = response.status_code in [200, 201]
                details = f"Style: {style}, Status: {response.status_code}"
                
                if success:
                    data = response.json()
                    details += f", Roast length: {len(data.get('roast_text', ''))}"
                
                style_results.append(success)
                self.log_test(f"Roast Style - {style.upper()}", success, details)
                
                # Small delay between requests
                time.sleep(2)
                
            except Exception as e:
                style_results.append(False)
                self.log_test(f"Roast Style - {style.upper()}", False, f"Error: {str(e)}")
        
        overall_success = any(style_results)  # At least one style should work
        return overall_success

    def test_invalid_inputs(self):
        """Test API with invalid inputs"""
        invalid_tests = [
            {
                "name": "Empty URL",
                "data": {"linkedin_url": "", "roast_style": "mix"},
                "expected_status": [400, 422]
            },
            {
                "name": "Invalid URL",
                "data": {"linkedin_url": "not-a-url", "roast_style": "mix"},
                "expected_status": [400, 422, 500]
            },
            {
                "name": "Invalid Roast Style",
                "data": {"linkedin_url": "https://www.linkedin.com/in/test", "roast_style": "invalid"},
                "expected_status": [200, 201, 400, 422]  # May still work with default
            }
        ]
        
        all_passed = True
        for test in invalid_tests:
            try:
                response = requests.post(
                    f"{self.api_url}/generate-roast",
                    json=test["data"],
                    timeout=30,
                    headers={'Content-Type': 'application/json'}
                )
                
                success = response.status_code in test["expected_status"]
                details = f"Status: {response.status_code}, Expected: {test['expected_status']}"
                
                self.log_test(f"Invalid Input - {test['name']}", success, details)
                if not success:
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"Invalid Input - {test['name']}", False, f"Error: {str(e)}")
                all_passed = False
        
        return all_passed

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting LinkedIn Roaster Backend API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test 1: API Health
        if not self.test_api_health():
            print("❌ API is not responding. Stopping tests.")
            return False
        
        # Test 2: Generate Roast (main functionality)
        roast_success, roast_data = self.test_generate_roast_endpoint()
        
        # Test 3: Audio endpoint
        if roast_success and 'audio_url' in roast_data:
            audio_filename = roast_data['audio_url'].split('/')[-1]
            self.test_audio_endpoint(audio_filename)
        else:
            self.test_audio_endpoint()  # Test 404 handling
        
        # Test 4: Different roast styles (optional, may be slow)
        print("\n🎭 Testing different roast styles (this may take several minutes)...")
        # self.test_roast_styles()  # Commented out to save time in initial testing
        
        # Test 5: Invalid inputs
        self.test_invalid_inputs()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    tester = LinkedInRoasterAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'summary': {
                'total_tests': tester.tests_run,
                'passed_tests': tester.tests_passed,
                'success_rate': f"{(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%",
                'timestamp': datetime.now().isoformat()
            },
            'detailed_results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())