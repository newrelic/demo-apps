# frozen_string_literal: true
require 'bundler/setup'
require "aws-sdk-dynamodb"

def lambda_handler(event:, context:)
  data = client.scan(table_name: ENV["RUBY_LAMBDA_TABLE"])
  items = data.items

  { statusCode: 200, body: items.to_json }
end

def client
  @client ||= Aws::DynamoDB::Client.new
end
