
            self.assertEqual(json_response.status_code, 200)
            self.assertIsNotNone(json_response.content)

            doi_json = json.loads(json_response.content.decode('utf-8'))

            # assert we obtained the correct doi
            self.assertEqual(doi_json.get('@id').lower(), 'https://doi.org/'+doi)

            # assert the required keys are in there
            self.assertTrue(all([key in doi_json.keys() for key in self.required_keys]))

            # assert all required keys are not empty
            self.assertTrue(all([doi_json.get(key) is not None for key in self.required_keys])) 

