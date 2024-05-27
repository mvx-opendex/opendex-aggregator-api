#!/bin/sh

cat ./urls.txt | while read url
do
  echo "${url}"

  curl -s "${url}" > .curl.out
  
  cat .curl.out | jq .static.net_amount_out
  
  cat .curl.out | jq .dynamic.net_amount_out

  sleep 0.1
done
