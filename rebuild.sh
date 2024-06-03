sudo docker build --tag lemma-server .
sudo docker run -d -p 5000:5000 lemma-server
