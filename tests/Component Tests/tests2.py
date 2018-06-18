
    def test_get_example(self):
        response = self.app.get('/minid/ark:/99999/fk4test')
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 200) 
        self.assertIsInstance(response, Response)
        self.assertIsInstance(response.data, bytes)


    def test_get_nonid(self):
        response = self.app.get('/minid/ark:/99999/fk4notarealid')
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(response,Response)
        self.assertIsInstance(response.data, bytes)

    def test_put_nobody(self):
        response = self.app.put('/minid/ark:/99999/fk4mytemp', headers=headers) 
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response, Response)

    def test_put_noauth(self):
        response = self.app.put('/minid/ark:/99999/fk4mytemp', data=testBody) 
        self.assertIsNotNone(response)
        self.assertIsInstance(response, Response) 
        self.assertEqual(response.status_code, 401)
        self.assertEqual(b"Missing Login information, cannot mint/updates IDs without authentication", response.data)

    def test_put_badbody(self):
        response = self.app.put('/minid/ark:/99999/fk4mytemp', headers=headers, data=badBody)
        self.assertIsNotNone(response)
        self.assertIsInstance(response,Response)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(b"Submitted Request Body was missing required parameters", response.data)

        
    #def test_update_tempid(self):
    #    pass
