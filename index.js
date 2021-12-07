const express = require('express')
const { spawn } = require('child_process')

const app = express()
const port = 3000

app.get('/', (req, res) => {

  let {folderId, viewOfDicomName, viewOfDicomSliceNumber, viewOfDicomThreshold } = req.query
  console.log('folderId, viewOfDicomName, viewOfDicomSliceNumber, viewOfDicomThreshold===', folderId, viewOfDicomName, viewOfDicomSliceNumber, viewOfDicomThreshold)
  let imageBase64 = []
  // spawn new child process to call the python script
  const python = spawn('python', ['server.py', folderId, viewOfDicomName, viewOfDicomSliceNumber, viewOfDicomThreshold])

  // collect data from script
  python.stdout.on('data', function (data) {
    console.log('Pipe data from python script ...', data)
    //dataToSend =  data;
    imageBase64.push(data)
  })

  // in close event we are sure that stream is from child process is closed
  python.on('close', (code) => {
    console.log(`child process close all stdio with code ${code}`)

    res.status(200).json(Buffer.concat(imageBase64).toString())
  })
})

app.listen(port, () => {
  console.log(`App listening on port ${port}!`)
})
